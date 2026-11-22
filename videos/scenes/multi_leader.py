from sfz import *

# sfz says PostgreSQL as "postgres", which the voice reads as "POST-gurz"; spell the vowel out
SAY.insert(0, (r"\bPostgreSQL\b", "post-gress"))
SAY.insert(0, (r"\bpgactive\b", "P G active"))
SAY.insert(0, (r"\ball-to-all\b", "all to all"))
SAY.insert(0, (r"\bpay-81723\b", "pay eight one seven two three"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
BW, BH = 3.6, 1.5
C = {"eu": np.array([-4.3, 1.55, 0]), "us": np.array([4.3, 1.55, 0]), "ap": np.array([0, -1.3, 0])}
NAME = {"eu": "eu  (Frankfurt)", "us": "us  (Virginia)", "ap": "ap  (Asia)"}
COL = {"eu": BLUE_M, "us": TEAL_M, "ap": PURPLE_M}
LINKS = {("eu", "us"): ([-4.3 + BW / 2 + 0.1, 1.55, 0], [4.3 - BW / 2 - 0.1, 1.55, 0]),
         ("eu", "ap"): ([-3.4, 0.7, 0], [-1.15, -0.45, 0]),
         ("us", "ap"): ([3.4, 0.7, 0], [1.15, -0.45, 0])}
DELAY = {("eu", "us"): 40, ("eu", "ap"): 150, ("us", "ap"): 30}
HELD_C = np.array([3.75, -1.55, 0])
CLOCK_C = np.array([0, 3.2, 0])
CAP_Y, BAR_Y = -3.25, -2.75
STAT = {"AUTHORIZED": GOLD_M, "CAPTURED": GREEN_M, "—": GREY_B}


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



def link_pts(a, b):
    if (a, b) in LINKS:
        p, q = LINKS[(a, b)]
        return np.array(p, dtype=float), np.array(q, dtype=float)
    p, q = LINKS[(b, a)]
    return np.array(q, dtype=float), np.array(p, dtype=float)


def msg(text, color):
    return chip(text, color, 14, mono=True).set_z_index(7)


class MultiLeader(Base):
    """repl-05, section 1. Three regions, each a leader, every leader sending to every other. Topologies: circle,
    star, all-to-all; the origin stops echoes; all-to-all's weakness is links of different speeds. pay-81723: eu's
    INSERT (40 ms to us, 150 ms to ap), us's capture at 45 ms reaches ap at 75 ms, before its insert. pgactive's
    default discards it: ap AUTHORIZED forever. Timestamps with us's clock 60 ms behind: everyone keeps the insert.
    Carrying causality ("needs eu: 1") holds the update until the insert lands: all CAPTURED. Version vector, moral,
    the limit (writes that never saw each other: next) and a check."""

    def status(self, r, s, color=None):
        m = T("pay-81723: no row", 20, GREY_B)
        if s != "—":
            m = VGroup(M("pay-81723", 18, GREY_B), T(s.lower(), 22, color or STAT.get(s, WHITE))).arrange(RIGHT, buff=0.25)
        return self.put("st" + r, m.move_to(C[r] + [0, -0.25, 0]))

    def clock(self, t):
        return self.put("clock", chip(f"{t} ms" if isinstance(t, int) else t, YELLOW_M, 24, mono=True).move_to(CLOCK_C))

    def outline(self, r, color):
        return [self.box[r].animate.set_stroke(color)]

    def send(self, key, text, color, a, b, t0):
        """Start a message from a to b at time t0 (in ms); it moves when advance() is called."""
        p0, q0 = link_pts(a, b)
        p, q = p0 + 0.2 * (q0 - p0), p0 + 0.8 * (q0 - p0)
        delay = DELAY.get((a, b)) or DELAY.get((b, a))
        if (a, b) == ("us", "eu"):
            delay = 40
        m = msg(text, color).move_to(p)
        self.msgs[key] = (m, p, q, t0, delay)
        self.lab["m" + key] = m
        return [FadeIn(m, scale=0.7)]

    def advance(self, t):
        out = []
        for k, (m, p, q, t0, d) in list(self.msgs.items()):
            f = min(1.0, max(0.0, (t - t0) / d))
            out.append(m.animate.move_to(p + f * (q - p)))
        return out + self.clock(t)

    def arrive(self, key):
        self.msgs.pop(key, None)
        return self.drop("m" + key)

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def reset(self):
        out = []
        for k in list(self.msgs):
            out += self.arrive(k)
        out += self.drop("held", "x", "note", "tick_eu", "tick_us", "tick_ap")
        for r in C:
            out += self.status(r, "—") + self.outline(r, COL[r])
        return out + self.clock(0)

    def construct(self):
        self.lab = {}
        self.msgs = {}
        self.title_card("The update that arrived first", "three leaders, one payment, two answers")

        # ---------------- scene 1: two answers forever ----------------
        self.box = {r: RoundedRectangle(corner_radius=0.14, width=BW, height=BH, stroke_color=COL[r], stroke_width=3)
                    .set_fill(fillc(COL[r]), 1).move_to(C[r]) for r in C}
        names = {r: T(NAME[r], 22).move_to(C[r] + [0, BH / 2 - 0.35, 0]) for r in C}
        lines = {k: Line(*v, stroke_width=2.5, color=GREY_C) for k, v in LINKS.items()}
        self.steps("Three databases, one in Frankfurt, one in Virginia, one in Asia. They all copy each other.", [
            "Three databases",
            (lambda: [LaggedStart(*[FadeIn(VGroup(self.box[r], names[r])) for r in C], lag_ratio=0.4)], 1.4),
            "They all copy",
            (lambda: [*[Create(l) for l in lines.values()]], 0.8),
        ])
        self.steps("Every message arrived. Nothing was lost. And yet, for one card payment, two of them say captured and the third says "
                   "authorized, and nothing will ever fix it.", [
            "two of them",
            (lambda: [*self.status("eu", "CAPTURED"), *self.status("us", "CAPTURED")], 0.6),
            "the third",
            (lambda: [*self.status("ap", "AUTHORIZED"), *self.outline("ap", RED_M)], 0.6),
        ])
        qm = T("?", 60, YELLOW_M).move_to(CLOCK_C + 0.1 * DOWN)
        self.steps("How do three careful copies end up disagreeing forever?", [
            (lambda: [FadeIn(qm, scale=0.6)], 0.6),
        ], after=0.5)

        # ---------------- scene 2: a leader in every region ----------------
        self.steps("Here's how we got here. A leader is the one database that takes writes and puts them in order in its log.", [
            (lambda: [FadeOut(qm), *[a for r in C for a in self.status(r, "—") + self.outline(r, COL[r])],
                      *[l.animate.set_opacity(0.15) for l in lines.values()]], 0.7),
            "A leader is",
            (lambda: [glow(self.box["us"], TEAL_M, 1.03), *self.cap("leader: takes the writes and puts them in order in its log", WHITE)], 0.9),
        ])
        self.steps("With customers on three continents, one leader means every card tap crosses an ocean. So each region gets its own leader.", [
            "every card tap",
            (lambda: [dot_run(C["eu"] + [BW / 2, 0, 0], C["us"] - [BW / 2, 0, 0], WHITE, 1.0)], 1.0),
            "So each region",
            (lambda: [LaggedStart(*[glow(self.box[r], COL[r], 1.03) for r in C], lag_ratio=0.3)], 1.2),
        ])
        self.steps("It saves its own customers' writes at once, and sends its log to the others a moment later.", [
            (lambda: [*self.cap("each region: a leader for its own customers, a follower of the others", WHITE),
                      *[l.animate.set_opacity(1) for l in lines.values()]], 0.8),
            "sends its log",
            (lambda: [dot_run(*link_pts("eu", "us"), YELLOW_M, 0.8), dot_run(*link_pts("eu", "ap"), YELLOW_M, 0.8)], 0.8),
        ])
        self.steps("Picture cafés that each keep a copy of the same notebook. Each café writes new lines in its own copy, "
                   "and phones the others its new lines a little later.", [
            (lambda: self.cap("cafés, each with a copy of the same notebook", GREY_B), 0.5),
            "and phones",
            (lambda: [dot_run(*link_pts("us", "ap"), YELLOW_M, 0.8), dot_run(*link_pts("us", "eu"), YELLOW_M, 0.8)], 0.8),
        ])
        self.steps("The notebooks are the databases, each café is a leader, and the phone calls carry the logs.", [
            (lambda: self.cap("notebook = database      café = leader      phone call = the log, sent", WHITE), 0.6),
            "phone calls",
            (lambda: [*[Indicate(l, color=YELLOW_M) for l in lines.values()]], 0.8),
        ])

        # ---------------- scene 3: who calls whom ----------------
        circ = VGroup(*[Arrow(*link_pts(a, b), buff=0, stroke_width=4, color=YELLOW_M, max_tip_length_to_length_ratio=0.08)
                        for a, b in (("eu", "us"), ("us", "ap"), ("ap", "eu"))])
        self.steps("With three cafés, who calls whom? In a circle, each one passes changes to the next.", [
            (lambda: [*self.drop("cap"), *[l.animate.set_opacity(0.2) for l in lines.values()]], 0.5),
            "In a circle",
            (lambda: [LaggedStart(*[GrowArrow(a) for a in circ], lag_ratio=0.4), *self.cap("a circle", YELLOW_M)], 1.2),
        ])
        self.steps("In a star, one hub hears everything and passes it on.", [
            (lambda: [FadeOut(circ), lines[("eu", "us")].animate.set_opacity(1), lines[("us", "ap")].animate.set_opacity(1),
                      *self.cap("a star: us is the hub", YELLOW_M)], 0.6),
            "one hub",
            (lambda: [glow(self.box["us"], YELLOW_M, 1.04)], 0.9),
        ])
        loop = VGroup(*[Line(*link_pts(a, b)) for a, b in (("eu", "us"), ("us", "ap"), ("ap", "eu"))])
        self.steps("Both forward, so a change could come home and go round forever.", [
            (lambda: [lines[("eu", "ap")].animate.set_opacity(1), *self.cap("forwarding: a change comes home, and goes round again", RED_M)], 0.4),
            (lambda: [Succession(*[dot_run(l.get_start(), l.get_end(), RED_M, 0.45) for l in list(loop) * 2])], 2.7),
        ])
        org = msg("origin: eu", YELLOW_M).move_to(C["eu"] + [0, -BH / 2 - 0.35, 0])
        self.steps("So every change carries its origin, where it was first written, and a café drops a change it has already applied.", [
            "carries its origin",
            (lambda: [FadeIn(org), *self.cap("every change carries its origin", WHITE)], 0.6),
            "drops a change",
            (lambda: [Succession(*[dot_run(l.get_start(), l.get_end(), YELLOW_M, 0.4) for l in loop])], 1.4),
            (lambda: [*self.put("x", tick(False, 0.15).move_to(C["eu"] + [BW / 2 - 0.35, -BH / 2 + 0.3, 0]))], 0.4),
        ])
        self.steps("Circles and stars depend on single cafés: lose the hub, and nobody hears anything.", [
            (lambda: [FadeOut(org), *self.drop("x"), lines[("eu", "ap")].animate.set_opacity(0.2)], 0.4),
            "lose the hub",
            (lambda: [*self.outline("us", RED_M), *self.cap("hub down: nobody hears anything", RED_M),
                      lines[("eu", "us")].animate.set_opacity(0.2), lines[("us", "ap")].animate.set_opacity(0.2)], 0.7),
        ])
        dl = {k: T(t, 20, c) for k, t, c in [(("eu", "us"), "40 ms", GREY_B), (("eu", "ap"), "150 ms (slow today)", RED_M),
                                              (("us", "ap"), "30 ms", GREY_B)]}
        dl[("eu", "us")].next_to(lines[("eu", "us")], UP, buff=0.38)
        dl[("eu", "ap")].move_to([-4.3, -0.35, 0])
        dl[("us", "ap")].move_to([3.55, -0.2, 0])
        self.steps("So all-to-all is the usual choice: everyone calls everyone. Its weakness is quieter. The lines run at different speeds.", [
            (lambda: [*self.outline("us", TEAL_M), *[l.animate.set_opacity(1) for l in lines.values()], *self.cap("all-to-all", WHITE)], 0.6),
            "different speeds",
            (lambda: [LaggedStart(*[FadeIn(v) for v in dl.values()], lag_ratio=0.3)], 1.0),
        ])

        # ---------------- scene 4: the update that overtakes ----------------
        self.steps("Two words for a card payment. When you tap, your bank sets the money aside, and the payment is authorized. "
                   "Later the money really moves, and it's captured.", [
            (lambda: [*self.cap("authorized: the money is set aside", GOLD_M)], 0.5),
            "Later the money",
            (lambda: [*self.cap("captured: the money really moves", GREEN_M)], 0.5),
        ])
        self.steps("At 0 ms, Frankfurt inserts payment pay-81723 as authorized, and sends the insert to both others.", [
            (lambda: [*self.drop("cap"), *self.clock(0)], 0.4),
            "inserts payment",
            (lambda: self.status("eu", "AUTHORIZED"), 0.5),
            "sends the insert",
            (lambda: [*self.send("i_us", "INSERT", GOLD_M, "eu", "us", 0), *self.send("i_ap", "INSERT", GOLD_M, "eu", "ap", 0)], 0.5),
        ])
        self.steps("Virginia gets it at 40 ms, and captures the payment at 45. It sends that update on.", [
            (lambda: self.advance(40), 1.2),
            (lambda: [*self.arrive("i_us"), *self.status("us", "AUTHORIZED")], 0.4),
            "captures",
            (lambda: [*self.advance(45), *self.status("us", "CAPTURED")], 0.5),
            "It sends",
            (lambda: [*self.send("u_ap", "UPDATE", GREEN_M, "us", "ap", 45), *self.send("u_eu", "UPDATE", GREEN_M, "us", "eu", 45)], 0.5),
        ])
        self.steps("Asia's line from Virginia takes 30 ms. Its line from Frankfurt takes 150. So what reaches Asia first? Pause and guess.", [
            "takes 30",
            (lambda: [Indicate(dl[("us", "ap")], color=WHITE)], 0.6),
            "takes 150",
            (lambda: [Indicate(dl[("eu", "ap")], color=RED_M)], 0.6),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        nsr = T("no such row", 18, RED_M).move_to(C["ap"] + [0, -BH / 2 + 0.22, 0])
        self.steps("The update, at 75 ms, for a row Asia doesn't have yet.", [
            (lambda: [*self.drop("cap"), *self.advance(75)], 1.4),
            (lambda: [*self.put("note", nsr), Indicate(self.lab["mu_ap"], color=RED_M)], 0.5),
        ])
        self.steps("pgactive, a free add-on from Amazon that lets several PostgreSQL servers all take writes, "
                   "documents its default for this case: throw the update away.", [
            "documents its default",
            (lambda: [*self.cap("pgactive's default: discard an update for a row it doesn't have", WHITE)], 0.5),
            "throw the update",
            (lambda: [*self.put("x", tick(False, 0.2).move_to(self.lab["mu_ap"])), *self.arrive("u_ap")], 0.6),
        ])
        self.steps("The insert lands at 150 ms. Asia says authorized, the others say captured, and no message is left on its way to repair it.", [
            (lambda: [*self.drop("x", "note"), *self.advance(85)], 0.6),
            (lambda: [*self.arrive("u_eu"), *self.status("eu", "CAPTURED")], 0.4),
            (lambda: self.advance(150), 1.2),
            (lambda: [*self.arrive("i_ap"), *self.status("ap", "AUTHORIZED"), *self.outline("ap", RED_M)], 0.5),
            "no message",
            (lambda: self.cap("final: eu captured, us captured, ap authorized, for good", RED_M), 0.5),
        ])
        self.steps("It's a call saying change that order to blue, about an order nobody has heard of yet. So the café shrugs, and bins it.", [
            "shrugs",
            (lambda: [Wiggle(self.box["ap"], scale_value=1.03)], 0.9),
        ], after=0.5)

        # ---------------- scene 5: timestamps, tested ----------------
        self.steps("You may be thinking: timestamps. Every leader keeps whichever version carries the later time.", [
            (lambda: self.reset(), 0.7),
            "keeps whichever",
            (lambda: self.cap("keep the version with the later time", WHITE), 0.5),
        ])
        skew = T("us clock: 60 ms behind", 20, RED_M).move_to(C["us"] + [0, BH / 2 + 0.35, 0])
        self.steps("But say Virginia's clock runs 60 ms behind Frankfurt's. Then the capture is stamped minus 15, and the insert 0.", [
            "Virginia's clock",
            (lambda: [*self.put("skew", skew)], 0.5),
            "the capture",
            (lambda: [*self.status("eu", "AUTHORIZED"), *self.send("i_us", "INSERT ts 0", GOLD_M, "eu", "us", 0),
                      *self.send("i_ap", "INSERT ts 0", GOLD_M, "eu", "ap", 0)], 0.5),
            (lambda: self.advance(40), 0.8),
            (lambda: [*self.arrive("i_us"), *self.status("us", "AUTHORIZED"), *self.advance(45)], 0.4),
            (lambda: [*self.send("u_ap", "UPDATE ts -15", GREEN_M, "us", "ap", 45), *self.send("u_eu", "UPDATE ts -15", GREEN_M, "us", "eu", 45)], 0.5),
        ])
        self.steps("Every region keeps the insert, Virginia included, so it ignores its own capture. They agree, on the wrong answer.", [
            (lambda: [*self.cap("-15 is earlier than 0: keep the insert", WHITE), glow(self.box["us"], RED_M, 1.03)], 0.5),
            (lambda: self.advance(75), 0.8),
            (lambda: [*self.arrive("u_ap"), *self.status("ap", "CAPTURED")], 0.4),
            (lambda: self.advance(85), 0.4),
            (lambda: [*self.arrive("u_eu")], 0.3),
            (lambda: self.advance(150), 0.8),
            (lambda: [*self.arrive("i_ap"), *self.status("ap", "AUTHORIZED")], 0.4),
            "They agree",
            (lambda: [*[a for r in C for a in self.outline(r, RED_M)], *self.cap("they agree, on a capture that never happened", RED_M)], 0.6),
        ])
        self.steps("A clock is a very confident witness, and that's all it is.", [
            (lambda: [Indicate(self.lab["clock"], color=RED_M)], 0.9),
        ], after=0.4)

        # ---------------- scene 6: say what you'd seen ----------------
        self.steps("What works is to carry what each change had already seen, instead of the time.", [
            (lambda: [*self.reset(), *self.drop("skew")], 0.7),
            "carry what",
            (lambda: self.cap("carry what each change had seen, not the time", YELLOW_M), 0.5),
        ])
        self.steps("Back at the cafés, Virginia's call starts: I've already heard Frankfurt's line 1.", [
            (lambda: [*self.status("eu", "AUTHORIZED"), *self.send("i_us", "INSERT eu:1", GOLD_M, "eu", "us", 0),
                      *self.send("i_ap", "INSERT eu:1", GOLD_M, "eu", "ap", 0)], 0.5),
            (lambda: self.advance(40), 0.8),
            (lambda: [*self.arrive("i_us"), *self.status("us", "AUTHORIZED"), *self.advance(45)], 0.4),
            (lambda: [*self.status("us", "CAPTURED"), *self.send("u_ap", "UPDATE needs eu:1", GREEN_M, "us", "ap", 45),
                      *self.send("u_eu", "UPDATE needs eu:1", GREEN_M, "us", "eu", 45)], 0.5),
        ])
        held_box = DashedVMobject(RoundedRectangle(corner_radius=0.1, width=2.7, height=0.7, stroke_color=YELLOW_M, stroke_width=2), num_dashes=40)
        held_box.move_to(HELD_C)
        held_t = T("held", 18, YELLOW_M).next_to(held_box, UP, buff=0.1)
        self.steps("Asia hasn't heard it yet, so it holds the update, and waits.", [
            (lambda: self.advance(75), 0.9),
            "holds the update",
            (lambda: [FadeIn(held_box), FadeIn(held_t), self.lab["mu_ap"].animate.move_to(HELD_C)], 0.6),
        ])
        self.msgs.pop("u_ap")
        self.steps("At 150 ms, the insert arrives. Asia applies it, sees the held update is now ready, and applies that too.", [
            (lambda: self.advance(85), 0.4),
            (lambda: [*self.arrive("u_eu"), *self.status("eu", "CAPTURED")], 0.4),
            (lambda: self.advance(150), 1.0),
            (lambda: [*self.arrive("i_ap"), *self.status("ap", "AUTHORIZED")], 0.4),
            "sees the held",
            (lambda: [self.lab["mu_ap"].animate.move_to(C["ap"]).set_opacity(0)], 0.6),
            (lambda: [*self.drop("mu_ap"), *self.status("ap", "CAPTURED"), FadeOut(held_box), FadeOut(held_t)], 0.4),
        ])
        self.steps("All three say captured, whatever the clocks read. That record, one counter per leader, is called a version vector.", [
            (lambda: [*[self.put("tick_" + r, tick(True, 0.17).move_to(C[r] + [BW / 2 - 0.3, BH / 2 - 0.3, 0]))[0] for r in C]], 0.7),
            "version vector",
            (lambda: self.cap("version vector: one counter per leader, saying what a change had seen", YELLOW_M), 0.6),
        ])

        # ---------------- scene 7: moral, guardrail, check ----------------
        self.steps("So how did three careful copies disagree forever? A later change took a faster line, and got thrown away.", [
            (lambda: [*self.cap("a later change took a faster line, and got thrown away", WHITE)], 0.6),
            "faster line",
            (lambda: [Indicate(dl[("us", "ap")], color=WHITE)], 0.7),
        ])
        self.steps("Carry what each change had seen, not what time it was.", [
            (lambda: self.cap("carry what you'd seen, not what time it was", YELLOW_M, 30), 0.6),
        ], after=0.5)
        self.steps("One limit: holding works because the update had seen the insert. Two writes that never saw each other are a harder problem, "
                   "and that's next.", [
            (lambda: self.cap("holding works because the update had seen the insert", WHITE), 0.5),
            "Two writes",
            (lambda: self.cap("two writes that never saw each other: next", GREY_B), 0.5),
        ])
        applied = T("applied from eu: 1", 18, GREY_B).move_to(C["ap"] + [0, -BH / 2 + 0.22, 0])
        self.steps("One quick check. An update says: needs Frankfurt's change 2. Asia has applied only change 1. What does Asia do? Pause and think.", [
            (lambda: [*self.drop("cap", "tick_eu", "tick_us", "tick_ap"), *self.clock("check")], 0.4),
            "An update says",
            (lambda: self.send("q", "UPDATE needs eu:2", GREEN_M, "us", "ap", 0), 0.4),
            (lambda: [self.lab["mq"].animate.move_to(self.msgs["q"][2])], 0.8),
            "Asia has applied",
            (lambda: self.put("note", applied), 0.5),
            "Pause and think",
            (lambda: [*self.cap("pause and think", YELLOW_M), *self.clock("check")], 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("It holds the update, until Frankfurt's change 2 arrives.", [
            (lambda: [*self.drop("cap"), FadeIn(held_box), FadeIn(held_t), self.lab["mq"].animate.move_to(HELD_C)], 0.7),
            "until",
            (lambda: self.cap("hold it until eu's change 2 arrives", YELLOW_M, 30), 0.5),
        ], after=0.3)
        self.wait(2.0)
