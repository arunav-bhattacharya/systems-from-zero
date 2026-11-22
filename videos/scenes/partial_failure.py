from sfz import *

SAY[0:0] = [
    (r"\b12\.50\b", "twelve fifty"),
    (r"\bpay-1\b", "pay one"),
]

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
B_TOP, B_BOT = 3.1, 1.0
B_CY = (B_TOP + B_BOT) / 2
BW = 2.8
SHOP_X, ISS_X = -5.0, 5.0
REQ_Y, ANS_Y = 2.45, 1.55                    # the two lanes of the network
LANE_X0, LANE_X1 = SHOP_X + BW / 2, ISS_X - BW / 2
TAG_Y = 3.37
HEAD_Y = 0.55
ROW_Y = [0.1 - 0.4 * i for i in range(6)]
COL_X = {"world": -6.3, "sees": -0.4, "charged": 2.4, "retry": 5.1}
BAR_Y, CAP_Y = -2.6, -3.2
WORLDS = [("the request is lost", "never"), ("the request waits in a queue", "at 5,050 ms"),
          ("the issuer crashed", "never"), ("the issuer is paused", "at 5,050 ms"),
          ("the answer is lost", "at 51 ms"), ("the answer is slow", "at 51 ms")]


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


def rbox(cx, cy, w, h, color):
    return RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(
        fillc(color), 1).move_to([cx, cy, 0])


def chip(s, color, y, x):
    t = M(s, 17, color)
    r = RoundedRectangle(corner_radius=0.08, width=t.width + 0.26, height=0.4, stroke_color=color, stroke_width=2).set_fill(BLACK, 1)
    return VGroup(r, t.move_to(r)).move_to([x, y, 0])


def pause_icon(at):
    return VGroup(*[RoundedRectangle(corner_radius=0.03, width=0.11, height=0.38, stroke_width=0).set_fill(GREY_B, 1).move_to(
        at + np.array([dx, 0, 0])) for dx in (-0.1, 0.1)])


class PartialFailure(Base):
    """dist-01, section 0. A card reader says "no reply" after 2 seconds: did the 12.50 go? On one computer a call
    returns, throws or dies, so silence feels like no. A text to a friend with no reply has six stories. The six worlds
    of pay-1 (lost, queued, crashed issuer, paused issuer, lost answer, slow answer) all look the same to the shop, and
    the card is charged in four. Waiting longer doesn't settle it: partial failure, three outcomes, a timeout starts
    unknown. Calling unknown a failure double-charges. The way out: one idempotency key for every retry. A check."""

    # --- small state helpers: each returns animations and updates what is on screen ---
    def cap(self, s, color=GREY_B, size=24):
        new = T(s, size, color).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def _set(self, key, new):
        old = self.st.get(key)
        self.st[key] = new
        if new is None:
            return [FadeOut(old)] if old is not None else []
        return [swap(old, new)]

    def shop_status(self, s, color=GREY_B):
        return self._set("shop", T(s, 20, color).move_to([SHOP_X, 1.3, 0]) if s else None)

    def timer(self, s, color=WHITE):
        return self._set("timer", M(s, 22, color).move_to([SHOP_X, 1.78, 0]) if s else None)

    def iss_status(self, s, color=GREY_B, when=None):
        if not s:
            return self._set("iss", None)
        g = VGroup(T(s, 20, color))
        if when:
            g.add((M if when[0].isdigit() or when.startswith("at ") else T)(when, 17, color))
        g.arrange(DOWN, buff=0.12).move_to([ISS_X, 1.62, 0])
        return self._set("iss", g)

    def run_timer(self, secs=1.2):
        """The 2,000 ms timer fills under the shop's clock, then runs out."""
        x0, x1 = SHOP_X - BW / 2 + 0.3, SHOP_X + BW / 2 - 0.3
        bar = Line([x0, 1.52, 0], [x1, 1.52, 0], stroke_width=4, color=YELLOW_M)
        self.st["tbar"] = bar
        return [Create(bar, run_time=secs, rate_func=linear)]

    def timed_out(self):
        anims = [*self.timer("2,000 ms", RED_M), *self.shop_status("no reply", RED_M)]
        bar = self.st.pop("tbar", None)
        if bar is not None:
            anims.append(FadeOut(bar))
        return anims

    def reset(self):
        anims = []
        for k in ("pkt", "ans", "x", "q", "icon", "late"):
            m = self.st.pop(k, None)
            if m is not None:
                anims.append(FadeOut(m))
        anims += [*self.timer("0 ms"), *self.shop_status("waiting", GREY_B), *self.iss_status("not charged"),
                  self.iss[0].animate.set_stroke(GOLD_M)]
        bar = self.st.pop("tbar", None)
        if bar is not None:
            anims.append(FadeOut(bar))
        return anims

    def send(self, to_x=None, rt=None):
        """pay-1 leaves the shop on the request lane and travels to to_x (default: into the issuer)."""
        p = chip("pay-1", YELLOW_M, REQ_Y, LANE_X0 + 0.55)
        self.st["pkt"] = p
        x = to_x if to_x is not None else ISS_X - BW / 2 - 0.1
        return [FadeIn(p, shift=0.15 * RIGHT), p.animate.move_to([x, REQ_Y, 0])]

    def arrive(self):
        p = self.st.pop("pkt", None)
        return [FadeOut(p, scale=0.6, target_position=[ISS_X, REQ_Y, 0])] if p is not None else []

    def answer(self, to_x=None):
        a = chip("approved", GREEN_M, ANS_Y, LANE_X1 - 0.8)
        self.st["ans"] = a
        x = to_x if to_x is not None else LANE_X0 + 0.8
        return [FadeIn(a, shift=0.15 * LEFT), a.animate.move_to([x, ANS_Y, 0])]

    def drop(self, key):
        m = self.st.pop(key, None)
        x = tick(False, 0.18).move_to(m.get_center())
        self.st["x"] = x
        return [FadeOut(m, scale=0.5), Create(x)]

    def qbox(self, y, label_x=-0.6):
        q = VGroup(RoundedRectangle(corner_radius=0.08, width=1.9, height=0.48, stroke_color=GREY_B, stroke_width=2),
                   T("queue", 16, GREY_B)).move_to([0, y, 0])
        q[1].move_to([label_x, y, 0])
        self.st["q"] = q
        return [FadeIn(q)]

    def row(self, i, show_charged=True):
        w, c = WORLDS[i]
        y = ROW_Y[i]
        g = VGroup(left_at(T(f"{i + 1}. {w}", 20), COL_X["world"], y), M("no reply", 18, RED_M).move_to([COL_X["sees"], y, 0]))
        cc = GREY_B if c == "never" else GOLD_M
        ch = M(c, 18, cc).move_to([COL_X["charged"], y, 0])
        self.rows[i] = g
        self.charged[i] = ch
        return [FadeIn(g, shift=0.1 * UP), FadeIn(ch, shift=0.1 * UP)] if show_charged else [FadeIn(g, shift=0.1 * UP)]

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def construct(self):
        self.capm = None
        self.st = {}
        self.rows, self.charged = [None] * 6, [None] * 6
        self.title_card("No reply: did it happen?", "one payment, a network, and six ways to hear nothing")

        # ---------------- scene 1: the till ----------------
        shop = VGroup(rbox(SHOP_X, B_CY, BW, B_TOP - B_BOT, BLUE_M), T("the shop", 24, BLUE_M).move_to([SHOP_X, 2.82, 0]),
                      M("pay-1  12.50", 18).move_to([SHOP_X, 2.33, 0]))
        reader_t = T("card reader", 24, BLUE_M).move_to([SHOP_X, 2.82, 0])
        self.steps("Picture the till at a busy café. You tap your card to pay 12.50 for lunch. "
                   "The card reader spins for two seconds, then says: no reply. Try again?", [
            (lambda: [FadeIn(shop[0]), FadeIn(shop[2]), FadeIn(reader_t), *self.timer("0 ms"), *self.shop_status("waiting")], 0.8),
            "spins",
            (lambda: self.run_timer(1.6), 1.6),
            "then says",
            (lambda: self.timed_out(), 0.5),
            "Try again",
            (lambda: self.cap("\"No reply. Try again?\"", RED_M), 0.5),
        ])
        self.steps("Did the money leave your account? Tap again, and you might pay twice. Walk away, and the café might never be paid.", [
            (lambda: self.cap("did the 12.50 leave your account?", WHITE), 0.5),
            "Tap again",
            (lambda: self.cap("tap again: maybe pay twice", GOLD_M), 0.5),
            "Walk away",
            (lambda: self.cap("walk away: maybe the café is never paid", GOLD_M), 0.5),
        ])
        self.steps("The reader can't tell you, because it doesn't know either. Why not? And what should it do?", [
            (lambda: self.cap("the reader doesn't know either", WHITE), 0.6),
        ])

        # ---------------- scene 2: one computer ----------------
        self.steps("Start with a program on one computer. When your code calls a function, it returns an answer, "
                   "or it throws an error, or the whole program stops, and nobody is left to be confused.", [
            (lambda: self.cap("one computer: a call returns, or throws, or everything stops", WHITE), 0.6),
            "nobody is left",
            (lambda: [glow(shop[0], BLUE_M, 1.02)], 0.8),
        ])
        self.steps("Code like that teaches us to expect two outcomes. So it's tempting to read no reply as no: it didn't happen.", [
            "two outcomes",
            (lambda: self.cap("two outcomes: yes or no", WHITE), 0.5),
            "So it's tempting",
            (lambda: self.cap("tempting: \"no reply\" means \"it didn't happen\"", YELLOW_M), 0.5),
        ])

        # ---------------- scene 3: two computers ----------------
        self.iss = VGroup(rbox(ISS_X, B_CY, BW, B_TOP - B_BOT, GOLD_M), T("the issuer", 24, GOLD_M).move_to([ISS_X, 2.82, 0]),
                          T("the card's bank", 17, GREY_B).move_to([ISS_X, 2.42, 0]))
        lanes = VGroup(Arrow([LANE_X0, REQ_Y, 0], [LANE_X1, REQ_Y, 0], buff=0.05, stroke_width=2.5, color=GREY_C,
                             max_tip_length_to_length_ratio=0.03),
                       Arrow([LANE_X1, ANS_Y, 0], [LANE_X0, ANS_Y, 0], buff=0.05, stroke_width=2.5, color=GREY_C,
                             max_tip_length_to_length_ratio=0.03))
        net_lab = T("the network", 20, GREY_B).move_to([0, 2.0, 0])
        self.steps("Now split the work across two computers. The card reader runs a small program; call it the shop. "
                   "To take the payment, the shop asks the bank that gave out the card to charge it. That bank is the card issuer.", [
            (lambda: [*self.uncap(), *self.timer("0 ms", WHITE), *self.shop_status("waiting")], 0.5),
            "call it the shop",
            (lambda: [swap(reader_t, shop[1])], 0.6),
            "the shop asks",
            (lambda: [FadeIn(self.iss), *self.iss_status("not charged")], 0.7),
        ])
        self.steps("They talk over a network: cables and boxes that carry messages between them. "
                   "Three parts, and each can break while the other two keep running. That's called partial failure.", [
            "over a network",
            (lambda: [GrowArrow(lanes[0]), GrowArrow(lanes[1]), FadeIn(net_lab)], 0.8),
            "Three parts",
            (lambda: [glow(shop[0], BLUE_M, 1.02), glow(self.iss[0], GOLD_M, 1.02), Indicate(net_lab, color=WHITE)], 0.9),
            "partial failure",
            (lambda: self.cap("partial failure: some parts break while the rest keep running", YELLOW_M), 0.6),
        ])

        # ---------------- scene 4: the text to a friend ----------------
        tags = [T("you", 19, GREY_B, slant=ITALIC).move_to([SHOP_X, TAG_Y, 0]),
                T("the phone network", 19, GREY_B, slant=ITALIC).move_to([0, TAG_Y, 0]),
                T("your friend", 19, GREY_B, slant=ITALIC).move_to([ISS_X, TAG_Y, 0])]
        self.steps("You've met this before. You text a friend: can you book us a table for Friday? Two minutes, no reply. What happened?", [
            (lambda: self.cap("\"Can you book us a table for Friday?\"", YELLOW_M), 0.5),
            "Two minutes",
            (lambda: self.cap("two minutes. no reply.", WHITE), 0.5),
        ])
        self.steps("Maybe the text never arrived. Maybe it's stuck, and arrives later. Maybe their phone died. "
                   "Maybe they're in the shower, and will see it in five minutes. Maybe they booked it, and their reply got lost. "
                   "Or the reply is just slow.", [
            (lambda: self.cap("never arrived?", WHITE), 0.4),
            "Maybe it's stuck",
            (lambda: self.cap("stuck, arriving later?", WHITE), 0.4),
            "Maybe their phone",
            (lambda: self.cap("their phone died?", WHITE), 0.4),
            "in the shower",
            (lambda: self.cap("in the shower?", WHITE), 0.4),
            "Maybe they booked",
            (lambda: self.cap("booked it, and the reply got lost?", WHITE), 0.4),
            "Or the reply",
            (lambda: self.cap("the reply is just slow?", WHITE), 0.4),
        ])
        self.steps("Six stories, and your phone looks exactly the same in all of them. "
                   "Your text is the request, the phone network is the network, and your friend is the issuer.", [
            (lambda: self.cap("six stories, one view", WHITE), 0.5),
            "Your text is",
            (lambda: [FadeIn(tags[0]), FadeIn(tags[1]), FadeIn(tags[2])], 0.8),
        ])
        self.steps("Do you book the table yourself? Maybe. Then you might have two tables, and one awkward phone call.", [
            "two tables",
            (lambda: self.cap("two tables, one awkward phone call", GOLD_M), 0.5),
        ], after=0.5)

        # ---------------- scene 5: predict, then six worlds ----------------
        head = VGroup(left_at(T("world", 19, GREY_B), COL_X["world"], HEAD_Y), T("the shop sees", 19, GREY_B).move_to([COL_X["sees"], HEAD_Y, 0]),
                      T("card charged", 19, GREY_B).move_to([COL_X["charged"], HEAD_Y, 0]))
        rule = Line([COL_X["world"], HEAD_Y - 0.22, 0], [6.4, HEAD_Y - 0.22, 0], stroke_width=1.5, color=GREY_D)
        self.steps("Let's run it for real. The shop sends pay-1, a request to charge 12.50, and starts a timer: 2,000 milliseconds, two seconds.", [
            (lambda: [*self.uncap(), FadeIn(head), Create(rule)], 0.6),
            "The shop sends",
            (lambda: [Indicate(shop[2], color=YELLOW_M)], 0.7),
            "starts a timer",
            (lambda: [Indicate(self.st["timer"], color=YELLOW_M)], 0.7),
        ])
        self.steps("We'll break it six ways. Before we do: in how many of the six does the card end up charged? Pause and guess.", [
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)

        # world 1: lost
        self.steps("World one: the request is lost. A box in the network had no room, and threw it away. "
                   "The issuer never hears of it.", [
            (lambda: [*self.uncap(), *self.reset()], 0.4),
            (lambda: [*self.send(-0.3), *self.run_timer(1.4)], 1.0),
            "threw it away",
            (lambda: self.drop("pkt"), 0.5),
            "never hears",
            (lambda: [*self.timed_out()], 0.5),
            (lambda: self.row(0), 0.5),
        ])
        # world 2: queue
        self.steps("World two: the request waits in a queue, a line of messages waiting their turn. "
                   "It reaches the issuer at 5,000 milliseconds, and the card is charged at 5,050. Three seconds after the shop gave up.", [
            (lambda: self.reset(), 0.4),
            (lambda: [*self.qbox(REQ_Y), *self.send(0.45), *self.run_timer(1.4)], 1.4),
            (lambda: self.timed_out(), 0.4),
            "It reaches",
            (lambda: [self.st["pkt"].animate.move_to([ISS_X - BW / 2 - 0.1, REQ_Y, 0])], 0.6),
            (lambda: [*self.arrive(), *self.iss_status("charged", GREEN_M, "at 5,050 ms")], 0.5),
            "Three seconds after",
            (lambda: self.row(1), 0.5),
        ])
        # world 3: crashed
        self.steps("World three: the issuer's program crashed before it charged the card.", [
            (lambda: self.reset(), 0.4),
            (lambda: [*self.send(), *self.run_timer(1.4)], 0.8),
            "crashed",
            (lambda: [*self.arrive(), self.iss[0].animate.set_stroke(RED_M), *self.iss_status("crashed", RED_M)], 0.5),
            (lambda: self.timed_out(), 0.4),
            (lambda: self.row(2), 0.5),
        ])
        # world 4: paused
        self.steps("World four: the issuer is paused. Some languages, Java among them, now and then stop a whole program "
                   "for a moment to clear out memory, and a bad pause can last seconds. At 5,000 milliseconds it carries on, "
                   "and charges the card at 5,050.", [
            (lambda: self.reset(), 0.4),
            (lambda: [*self.send(), *self.run_timer(1.4)], 0.8),
            (lambda: [*self.arrive(), *self.iss_status("paused", GREY_B, "pay-1 unread")], 0.6),
            "a bad pause",
            (lambda: self.timed_out(), 0.4),
            "At 5,000",
            (lambda: self.iss_status("charged", GREEN_M, "at 5,050 ms"), 0.6),
            (lambda: self.row(3), 0.5),
        ])
        # world 5: answer lost
        self.steps("World five: the card was charged at 51 milliseconds, and the answer was lost on the way back.", [
            (lambda: self.reset(), 0.4),
            (lambda: [*self.send(), *self.run_timer(1.4)], 0.8),
            "charged at 51",
            (lambda: [*self.arrive(), *self.iss_status("charged", GREEN_M, "at 51 ms")], 0.5),
            (lambda: self.answer(0.2), 0.6),
            "lost on the way",
            (lambda: self.drop("ans"), 0.5),
            (lambda: self.timed_out(), 0.4),
            (lambda: self.row(4), 0.5),
        ])
        # world 6: answer slow
        self.steps("World six: the card was charged at 51 milliseconds, and the answer is just slow. "
                   "It lands at 5,051, after the shop has already decided.", [
            (lambda: self.reset(), 0.4),
            (lambda: [*self.send(), *self.run_timer(1.4)], 0.8),
            "charged at 51",
            (lambda: [*self.arrive(), *self.iss_status("charged", GREEN_M, "at 51 ms")], 0.5),
            (lambda: [*self.qbox(ANS_Y, 0.62), *self.answer(-0.3)], 0.8),
            "just slow",
            (lambda: self.timed_out(), 0.4),
            "It lands",
            (lambda: [self.st["ans"].animate.move_to([LANE_X0 + 0.8, ANS_Y, 0])], 0.6),
            "after the shop",
            (lambda: [self.st["ans"].animate.set_opacity(0.35), *self.row(5)], 0.6),
        ])

        # ---------------- scene 6: count, and the break ----------------
        self.steps("Count the last column. Never charged: twice. Already charged: twice. Charged later: twice. "
                   "Four of the six. And the shop's column? The same in every row: no reply.", [
            (lambda: self.reset(), 0.4),
            "Never charged",
            (lambda: [Indicate(self.charged[0], color=GREY_B), Indicate(self.charged[2], color=GREY_B)], 0.7),
            "Already charged",
            (lambda: [Indicate(self.charged[4], color=GOLD_M), Indicate(self.charged[5], color=GOLD_M)], 0.7),
            "Charged later",
            (lambda: [Indicate(self.charged[1], color=GOLD_M), Indicate(self.charged[3], color=GOLD_M)], 0.7),
            "Four of the six",
            (lambda: self.cap("charged in four of the six", GOLD_M), 0.5),
            "The same in every",
            (lambda: [LaggedStart(*[Indicate(r[1], color=RED_M) for r in self.rows], lag_ratio=0.15),
                      *self.cap("the shop sees the same thing in all six", RED_M)], 1.2),
        ])
        self.steps("So wait longer? Pick ten seconds instead of two. A queue or a pause can always last longer than whatever you pick. "
                   "Waiting doesn't settle it.", [
            (lambda: self.cap("wait ten seconds instead?", WHITE), 0.5),
            "A queue or a pause",
            (lambda: [Indicate(self.rows[1][0], color=YELLOW_M), Indicate(self.rows[3][0], color=YELLOW_M)], 0.8),
            "Waiting doesn't",
            (lambda: self.cap("any queue or pause can outlast any timeout", RED_M), 0.5),
        ])

        # ---------------- scene 7: three outcomes ----------------
        self.steps("So a call to another machine has three outcomes: yes, no, and unknown. "
                   "A timeout is just the moment the shop stops waiting. It marks the start of unknown, nothing more.", [
            "three outcomes",
            (lambda: self.cap("three outcomes:  yes,  no,  unknown", YELLOW_M), 0.6),
            "A timeout is",
            (lambda: [*self.timed_out(), *self.shop_status("unknown", YELLOW_M)], 0.6),
            "start of unknown",
            (lambda: self.cap("a timeout: the start of unknown", YELLOW_M), 0.5),
        ])
        self.steps("And if the reader turns unknown into no, and says payment failed, you tap again. "
                   "In four of the six worlds, that charges you twice.", [
            "says payment failed",
            (lambda: self.shop_status("payment failed", RED_M), 0.5),
            "In four",
            (lambda: [*[Indicate(self.charged[i], color=RED_M, scale_factor=1.3) for i in (1, 3, 4, 5)],
                      *self.cap("unknown read as no: charged twice", RED_M)], 0.9),
        ])
        self.steps("So the rule is short. Silence is not an answer. Treat it as unknown.", [
            "Silence",
            (lambda: [*self.cap("silence is not an answer. treat it as unknown.", YELLOW_M, 28), *self.shop_status("unknown", YELLOW_M)], 0.7),
        ], after=0.6)

        # ---------------- scene 8: the way out ----------------
        rhead = T("retry, same key", 19, GREY_B).move_to([COL_X["retry"], HEAD_Y, 0])
        self.steps("So what can the shop do? Ask again, safely. Before the first attempt, it gives the payment a unique label, "
                   "and sends the same label with every retry. That label is an idempotency key.", [
            (lambda: self.uncap(), 0.3),
            "a unique label",
            (lambda: [Transform(shop[2], M("pay-1  key k-1", 18, YELLOW_M).move_to(shop[2]))], 0.6),
            "the same label",
            (lambda: [*self.send(), FadeIn(rhead)], 0.8),
            (lambda: self.arrive(), 0.3),
            "idempotency key",
            (lambda: self.cap("idempotency key: one label per payment, on every attempt", YELLOW_M), 0.6),
        ])
        self.steps("Idempotent means doing it twice has the same effect as doing it once. "
                   "The issuer remembers the labels it has charged, so a repeat gets the first answer back, not a second charge.", [
            "The issuer remembers",
            (lambda: [*self.iss_status("seen k-1", GREEN_M, "same answer back")], 0.6),
            "a repeat",
            (lambda: [*self.send(), *self.answer()], 0.9),
            (lambda: [*self.arrive()], 0.3),
        ])
        once = [M("once", 18, GREEN_M).move_to([COL_X["retry"], ROW_Y[i], 0]) for i in range(6)]
        self.steps("Where the card wasn't charged yet, the retry charges it once. Where it was, the retry gets the stored answer. "
                   "Either way, never twice.", [
            (lambda: [FadeOut(self.st.pop("ans"))], 0.3),
            "Where the card wasn't",
            (lambda: [FadeIn(once[0]), FadeIn(once[2])], 0.5),
            "Where it was",
            (lambda: [LaggedStart(*[FadeIn(once[i]) for i in (1, 3, 4, 5)], lag_ratio=0.2)], 0.8),
            "never twice",
            (lambda: [*self.cap("at most one charge, in every world", GREEN_M)], 0.5),
        ])
        self.steps("It's like texting: please book a table under the name Sam. Get that text twice, and there's still one table under Sam.", [
            "under the name Sam",
            (lambda: self.cap("\"book a table under the name Sam\": one table, however many texts", YELLOW_M), 0.6),
        ], after=0.5)

        # ---------------- scene 9: a check ----------------
        self.steps("One quick check. In world five, the answer is lost, and the shop retries with a brand new label every time. "
                   "How many charges? Pause and think.", [
            (lambda: [*self.uncap(), *self.reset(), *[Indicate(m, color=WHITE) for m in self.rows[4]]], 0.6),
            "brand new label",
            (lambda: [Transform(shop[2], M("pay-1  key k-2", 18, RED_M).move_to(shop[2]))], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Two. A new label looks like a new payment. Make the key once, before the first attempt.", [
            (lambda: [*self.uncap(), *self.iss_status("charged twice", RED_M, "k-1, then k-2")], 0.6),
            "Make the key once",
            (lambda: self.cap("make the key once, before the first attempt", YELLOW_M, 30), 0.6),
        ], after=0.3)
        self.steps("Silence has six causes, and the shop can't tell them apart. So treat it as unknown, and ask again with the same key.", [
            (lambda: [Transform(shop[2], M("pay-1  key k-1", 18, YELLOW_M).move_to(shop[2])), *self.shop_status("unknown", YELLOW_M),
                      *self.iss_status("charged once", GREEN_M)], 0.7),
            "ask again",
            (lambda: self.cap("unknown, then ask again with the same key", YELLOW_M, 30), 0.6),
        ], after=0.3)
        self.wait(2.0)
