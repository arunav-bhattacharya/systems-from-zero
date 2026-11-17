from sfz import *

SAY.insert(0, (r"\b1\.16 million\b", "one point one six million"))
SAY.insert(0, (r"\b3\.5 seconds\b", "three and a half seconds"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
PX, PW, PH = -5.35, 2.2, 0.9                  # the senders' own piles of letters, on the left
PILE_Y = {"Ana": 2.3, "Ben": 1.1, "Eli": -0.1}
SING = np.array([-5.25, -1.6, 0])              # the singer, bottom left
Q_Y, Q_FRONT = 1.1, -1.4                      # the queue (a tray of letters), front on the right
CK, CK_W, CK_H = np.array([0.1, 1.1, 0]), 2.1, 1.1       # the clerks, later the fan-out workers
WX0, CW, CH, GAP = 1.75, 1.1, 1.0, 0.1        # the wall of pigeonholes, 4 by 3
ROW_Y = [2.45, 1.35, 0.25]
NAMES = {(2, 0): "Cleo", (2, 1): "Ben", (2, 2): "Eli"}
RD, RD_W, RD_H = np.array([WX0 + CW / 2, -1.0, 0]), 1.9, 0.85  # Cleo, coming for her mail
BAR_X0, BAR_X1, BAR_Y = -3.6, 1.0, -2.0       # the singer's deliveries
CD_Y, CAP_Y = -2.55, -3.2


def hole_c(r, c):
    return np.array([WX0 + CW / 2 + c * (CW + GAP), ROW_Y[r], 0])


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
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    """Replace one label with another: the old one leaves before the new one arrives, so they never overlap."""
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def dot_to(a, b, color=YELLOW_M, rt=0.6):
    d = Dot(radius=0.07, color=color).move_to(a)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.12))


def card(c, w, h, color, top, sub=None, top_size=24, sub_size=18):
    c = np.array(c, dtype=float)
    r = RoundedRectangle(corner_radius=0.12, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1).move_to(c)
    if sub is None:
        return VGroup(r, T(top, top_size).move_to(c))
    k = h / 0.9
    return VGroup(r, T(top, top_size).move_to(c + [0, 0.17 * k, 0]), T(sub, sub_size, GREY_B).move_to(c + [0, -0.2 * k, 0]))


def letter(text, color=WHITE, w=None):
    t = M(text, 18, color)
    r = RoundedRectangle(corner_radius=0.06, width=w or max(0.6, t.width + 0.24), height=0.42, stroke_color=color, stroke_width=2).set_fill(BLACK, 1)
    return VGroup(r, t)


class HomeTimeline(Base):
    """found-04, section 2. A pop singer's one post makes everyone's feed late. The mail room: one pile per sender (fan-out
    on read, 400 million lookups a second), then pigeonholes sorted the moment a letter arrives (fan-out on write, 1.16
    million writes a second, 345 times less). Bursts wait in a queue for the clerks (fan-out workers). Twitter 2012.
    The singer: 31 million writes, about 108 seconds, and the café's 300-follower post waits behind it: the celebrity
    problem. Moral, a teaser for the hybrid, and a check question."""

    # --- small state helpers: each returns animations and updates what is on screen ---
    def cap(self, s, color=GREY_B, size=24):
        new = (T(s, size, color) if isinstance(s, str) else s)
        fit(new, 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def put(self, key, mob):
        old = self.lab.get(key)
        self.lab[key] = mob
        return [swap(old, mob)]

    def drop(self, *keys):
        out = []
        for k in keys:
            m = self.lab.pop(k, None)
            if m is not None:
                out.append(FadeOut(m))
        return out

    def countdown(self, secs=3.0):
        bar = Line([-1.0, CD_Y, 0], [1.0, CD_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("One post, 31 million writes", "the home timeline, built in advance")

        # ---------------- scene 1: the symptom ----------------
        sing = card([-3.4, 0.4, 0], 4.4, 1.5, GOLD_M, "a pop singer", "31 million followers", 34, 24)
        cafe = card([3.4, 0.4, 0], 4.4, 1.5, TEAL_M, "the café", "300 followers", 34, 24)
        late = T("late, for minutes", 28, RED_M).move_to([3.4, -0.85, 0])
        feed = T("your feed: the newest posts from the 200 accounts you follow", 28, WHITE).move_to([0, 2.4, 0])
        self.steps("Open a social app and pull down to refresh. In under a second, you see the newest posts from the 200 accounts you follow.", [
            "In under a second",
            (lambda: [FadeIn(feed, shift=0.1 * DOWN)], 0.8),
        ])
        self.steps("Then a pop singer with 31 million followers posts a photo. For the next few minutes, posts arrive late for everybody. "
                   "Even the café's post about today's cake, which only 300 people follow.", [
            (lambda: [FadeIn(sing, shift=0.2 * RIGHT)], 0.8),
            "For the next",
            (lambda: [feed.animate.set_color(RED_M)], 0.6),
            "Even the café's",
            (lambda: [FadeIn(cafe, shift=0.2 * LEFT)], 0.8),
            (lambda: [FadeIn(late, shift=0.1 * UP)], 0.6),
        ])
        qm = T("?", 64, YELLOW_M).move_to([0, 0.6, 0])
        self.steps("Why would one person's post make everyone else's late?", [
            (lambda: [FadeIn(qm, scale=0.6)], 0.6),
        ], after=0.5)

        # ---------------- scene 2: the mail room, one pile per sender ----------------
        piles = {n: card([PX, y, 0], PW, PH, BLUE_M, f"{n}'s letters", None, 26) for n, y in PILE_Y.items()}
        rd = card(RD, RD_W, RD_H, PURPLE_M, "Cleo", "comes for mail", 26, 19)
        self.steps("Picture the app as the mail room of a big office. The simplest plan keeps one pile of letters for each sender. "
                   "One for Ana, one for Ben, one for Eli.", [
            (lambda: [FadeOut(VGroup(sing, cafe, late, feed, qm))], 0.7),
            "mail room",
            (lambda: [LaggedStart(*[FadeIn(p, shift=0.1 * RIGHT) for p in piles.values()], lag_ratio=0.3)], 1.2),
        ])
        reads = VGroup(*[Line(RD + [-RD_W / 2 - 0.08, 0, 0], [PX + PW / 2 + 0.08, y, 0], stroke_width=2, color=PURPLE_M)
                         for y in PILE_Y.values()])
        self.steps("When Cleo comes for her mail, a clerk goes through the pile of everyone she follows, and picks out what's new. "
                   "Three piles here. On a real app, about 200.", [
            (lambda: [FadeIn(rd, shift=0.1 * UP)], 0.6),
            "a clerk goes",
            (lambda: [LaggedStart(*[Create(l) for l in reads], lag_ratio=0.3)], 1.0),
            (lambda: [LaggedStart(*[dot_to(l.get_end(), l.get_start(), PURPLE_M, 0.8) for l in reads], lag_ratio=0.3)], 1.4),
            "Three piles",
            (lambda: self.put("look", T("3 lookups per read", 22, PURPLE_M).move_to(RD + [0, -0.72, 0])), 0.5),
            "about 200",
            (lambda: self.put("look", T("about 200 lookups per read", 22, PURPLE_M).move_to(RD + [0, -0.72, 0])), 0.5),
        ])
        self.steps("That's called fan-out on read: the work happens when someone reads. And people read a lot. "
                   "With 2 million refreshes a second, each looking through about 200 piles, that's 400 million lookups a second.", [
            (lambda: self.cap("fan-out on read: the work happens when someone reads", WHITE), 0.6),
            "With 2 million",
            (lambda: [LaggedStart(*[dot_to(l.get_end(), l.get_start(), PURPLE_M, 0.6) for l in reads for _ in range(2)], lag_ratio=0.12)], 1.6),
            "that's 400",
            (lambda: self.cap("2 million reads a second × 200 piles  =  400 million lookups a second", RED_M), 0.7),
        ])
        self.steps("Wouldn't it be nice if Cleo's mail were already sorted when she came for it?", [
            (lambda: self.cap("already sorted when she comes?", YELLOW_M), 0.6),
        ], after=0.5)

        # ---------------- scene 3: pigeonholes ----------------
        holes = {}
        for r in range(3):
            for c in range(4):
                holes[(r, c)] = RoundedRectangle(corner_radius=0.06, width=CW, height=CH, stroke_color=GREY_B, stroke_width=2.5) \
                    .set_fill(BLACK, 1).move_to(hole_c(r, c))
        hnames = VGroup(*[T(n, 19, GREY_B).move_to(hole_c(*k) + [0, 0.24, 0]) for k, n in NAMES.items()])
        wall_t = T("pigeonholes", 24, GREY_B).move_to([WX0 + 2 * (CW + GAP) - GAP / 2, 3.25, 0])
        wall = VGroup(*holes.values())
        ck = card(CK, CK_W, CK_H, TEAL_M, "clerks", "sort each letter", 26, 19)
        wall_t2 = T("ready-made timelines", 24, GREY_B).move_to(wall_t)
        ck_w = T("fan-out", 26).move_to(ck[1])
        ck_w2 = T("workers", 19, GREY_B).move_to(ck[2])
        content = {}

        def put_in(k, text, color=WHITE):
            new = M(text, 19, color).move_to(hole_c(*k) + [0, -0.2 if k in NAMES else 0, 0])
            old, content[k] = content.get(k), new
            return swap(old, new)

        self.steps("So turn it around. Give everyone a pigeonhole, their own small box on the wall. The moment a letter arrives, "
                   "a clerk sorts it into the pigeonhole of everyone who follows its sender.", [
            (lambda: [*self.uncap(), FadeOut(reads), *self.drop("look")], 0.6),
            "Give everyone",
            (lambda: [LaggedStart(*[FadeIn(h, scale=0.8) for h in wall], lag_ratio=0.05), FadeIn(hnames), FadeIn(wall_t)], 1.2),
            "a clerk sorts",
            (lambda: [FadeIn(ck, shift=0.1 * UP)], 0.6),
        ])
        p7 = letter("p7", BLUE_M).move_to([PX + PW / 2 + 0.5, PILE_Y["Ana"], 0])
        fol = [(2, 0), (2, 1), (2, 2)]
        self.steps("Ana posts. Her followers are Cleo, Ben and Eli, so her post goes into three pigeonholes. Three writes.", [
            (lambda: [FadeIn(p7, shift=0.2 * RIGHT), glow(piles["Ana"][0], BLUE_M)], 0.6),
            (lambda: [p7.animate.move_to(CK + [-CK_W / 2 - 0.45, 0, 0])], 0.8),
            "so her post",
            (lambda: [FadeOut(p7, scale=0.6), *[dot_to(CK + [CK_W / 2, 0, 0], hole_c(*k), BLUE_M, 0.7) for k in fol]], 0.9),
            (lambda: [*[put_in(k, "p7", BLUE_M) for k in fol]], 0.4),
            "Three writes",
            (lambda: self.put("writes", T("3 writes", 22, TEAL_M).move_to(CK + [0, -0.85, 0])), 0.5),
        ])
        rd2 = card(RD, RD_W, RD_H, PURPLE_M, "Cleo", "1 lookup", 26, 19)
        up = Arrow(RD + [0, RD_H / 2 + 0.06, 0], hole_c(2, 0) + [0, -CH / 2 - 0.06, 0], buff=0, stroke_width=3, color=PURPLE_M,
                   max_tip_length_to_length_ratio=0.35)
        self.steps("Now Cleo comes for her mail. One lookup, of a list that's already sorted, newest first.", [
            "One lookup",
            (lambda: [GrowArrow(up), swap(rd[2], rd2[2])], 0.6),
            (lambda: [glow(holes[(2, 0)], PURPLE_M, 1.06)], 0.8),
        ])
        self.steps("In the app, each pigeonhole is a ready-made timeline: a list of post numbers, kept for every user. "
                   "This design is called fan-out on write, because the work happens when someone posts.", [
            "each pigeonhole",
            (lambda: [swap(wall_t, wall_t2), LaggedStart(*[glow(h, GREY_B, 1.04) for h in wall], lag_ratio=0.04)], 1.0),
            "This design",
            (lambda: self.cap("fan-out on write: the work happens when someone posts", WHITE), 0.6),
        ])
        self.steps("It's a copy, worked out from the posts and the follows, so it could be thrown away and rebuilt. "
                   "It exists only to make reads cheap, and you pay for it on every post: one write per follower.", [
            "It exists",
            (lambda: self.cap("cheap reads, paid for on every post: one write per follower", WHITE), 0.6),
            "one write per",
            (lambda: [*[dot_to(CK + [CK_W / 2, 0, 0], hole_c(*k), BLUE_M, 0.6) for k in fol]], 0.8),
        ])

        # ---------------- scene 4: count it ----------------
        self.steps("Let's count it with the same round numbers. 5,800 posts a second, each to 200 followers, is about 1.16 million writes a second. "
                   "Against 400 million lookups, that's about 345 times less work.", [
            (lambda: self.cap("5,800 posts a second × 200 followers  =  1.16 million writes a second", WHITE), 0.6),
            "Against 400",
            (lambda: self.cap(VGroup(T("on read: 400 million lookups", 24, RED_M), T("on write: 1.16 million writes", 24, GREEN_M),
                                     T("about 345 times less", 24, YELLOW_M)).arrange(RIGHT, buff=0.5)), 0.7),
        ])
        self.steps("Why such a gap? Look at one author. The follower count is on both sides. So the question is which happens more often: "
                   "posting, or reading. People refresh their feeds far more often than their friends post.", [
            (lambda: [*self.uncap(), glow(piles["Ana"][0], BLUE_M)], 0.6),
            "The follower count",
            (lambda: self.cap("one author: a write per follower, per post   vs   a lookup per follower, per read", WHITE), 0.6),
            "People refresh",
            (lambda: [glow(rd[0], PURPLE_M), *self.cap("reads happen far more often than posts", GREEN_M)], 0.8),
        ])
        tray = VGroup(*[RoundedRectangle(corner_radius=0.06, width=0.6, height=0.42, stroke_color=GREY_C, stroke_width=1.5)
                        .set_fill(BLACK, 1).move_to([Q_FRONT - 0.33 - 0.66 * k, Q_Y, 0]) for k in range(4)])
        tray_t = T("the queue", 20, GREY_B).move_to([Q_FRONT - 1.34, Q_Y - 0.5, 0])
        burst = VGroup(*[letter("p", WHITE, 0.6).move_to([Q_FRONT - 0.33 - 0.66 * k, Q_Y, 0]) for k in range(4)])
        self.steps("Bursts are fine too. If 150,000 posts land in one second, the letters wait in a queue, and the clerks, "
                   "called fan-out workers, catch up over the next few minutes. Posts appear a little late, and reads stay fast.", [
            (lambda: [*self.uncap(), FadeIn(tray), FadeIn(tray_t), *self.drop("writes")], 0.6),
            "If 150,000",
            (lambda: [LaggedStart(*[FadeIn(b, shift=0.3 * RIGHT) for b in burst], lag_ratio=0.2),
                      *self.cap("150,000 posts in one second: they wait in the queue", WHITE)], 1.0),
            "called fan-out",
            (lambda: [swap(ck[1], ck_w), swap(ck[2], ck_w2)], 0.7),
            "catch up",
            (lambda: [LaggedStart(*[b.animate.move_to(CK).set_opacity(0) for b in reversed(burst)], lag_ratio=0.3),
                      LaggedStart(*[dot_to(CK + [CK_W / 2, 0, 0], hole_c(r, c), WHITE, 0.6) for r in range(3) for c in range(4)], lag_ratio=0.08)], 2.2),
            "reads stay fast",
            (lambda: [glow(holes[(2, 0)], PURPLE_M, 1.06), glow(up, PURPLE_M, 1.0)], 0.8),
        ])

        # ---------------- scene 5: Twitter's numbers ----------------
        self.steps("Twitter ran this design in 2012. It served about 300,000 timeline reads a second, against about 5,000 new posts.", [
            (lambda: self.cap("Twitter, 2012:  about 300,000 timeline reads a second,  about 5,000 new posts", WHITE), 0.7),
        ])
        self.steps("The goal: every post in every follower's timeline within 5 seconds. Reaching a million followers took about 3.5 seconds.", [
            (lambda: self.cap("goal: every follower within 5 s.   a million followers: about 3.5 s", GREEN_M), 0.7),
        ])

        # ---------------- scene 6: the singer ----------------
        sg = card(SING, 2.6, 1.0, GOLD_M, "the singer", "31 million followers", 24, 18)
        s_post = letter("singer", GOLD_M).move_to([PX + 1.95, SING[1], 0])
        c_post = letter("café", TEAL_M)
        bar_bg = Line([BAR_X0, BAR_Y, 0], [BAR_X1, BAR_Y, 0], stroke_width=10, color=GREY_D)
        prog = ValueTracker(0.0)
        bar = always_redraw(lambda: Line([BAR_X0, BAR_Y, 0], [BAR_X0 + max(0.001, prog.get_value()) * (BAR_X1 - BAR_X0), BAR_Y, 0],
                                         stroke_width=10, color=GOLD_M))
        bar_l = left_at(T("the singer's post: 31 million writes", 20, GOLD_M), BAR_X0, BAR_Y + 0.35)
        clk_cache = {}

        def clk():
            s = f"{prog.get_value() * 108.5:.0f} s"
            if s not in clk_cache:
                clk_cache[s] = T(s, 26, WHITE)
            return clk_cache[s].copy().move_to([BAR_X1 + 0.6, BAR_Y, 0])
        clock = always_redraw(clk)
        many = T("× 31 million", 24, GOLD_M).move_to([5.3, -1.0, 0])
        self.steps("Now the singer posts. She had 31 million followers. So one post is 31 million writes. "
                   "At a million every 3.5 seconds, how long does it take? Pause and guess.", [
            (lambda: [*self.uncap(), FadeIn(sg, shift=0.2 * RIGHT), FadeOut(tray)], 0.7),
            "So one post",
            (lambda: [FadeIn(s_post, shift=0.2 * RIGHT), FadeIn(many, shift=0.1 * UP)], 0.6),
            (lambda: [s_post.animate.move_to([Q_FRONT - s_post.width / 2, Q_Y, 0])], 0.8),
            "At a million",
            (lambda: [Create(bar_bg), FadeIn(bar_l), FadeIn(bar), FadeIn(clock)], 0.6),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        c_post.move_to([Q_FRONT - s_post.width - 0.14 - c_post.width / 2, Q_Y, 0])
        cafe_fol = T("300 followers", 18, TEAL_M).next_to(c_post, DOWN, buff=0.14)

        def dots(n):
            return LaggedStart(*[dot_to(CK + [CK_W / 2, 0, 0], hole_c((k * 5) % 3, (k * 7) % 4), GOLD_M, 0.5) for k in range(n)],
                               lag_ratio=0.3)

        def deliver(to, rt):
            return [prog.animate(rate_func=linear).set_value(to), dots(int(rt * 4))]

        self.steps("About 108 seconds. In practice, deliveries took up to 5 minutes.", [
            (lambda: [*self.uncap(), glow(s_post[0], GOLD_M, 1.1)], 0.6),
            (lambda: deliver(1.0, 3.2), 3.2),
            "In practice",
            (lambda: self.cap("about 108 seconds.   in practice: up to 5 minutes", RED_M), 0.6),
        ])
        self.steps("And the clerks take letters from the queue in order. So the café's post, with only 300 followers, waits behind 31 million writes.", [
            (lambda: [*self.uncap(), FadeOut(tray_t), glow(ck[0], TEAL_M)], 0.6),
            "So the café's",
            (lambda: [FadeIn(c_post, shift=0.2 * RIGHT), FadeIn(cafe_fol)], 0.6),
            "waits behind",
            (lambda: [dots(8), c_post[0].animate.set_stroke(RED_M), *self.cap("the café's post waits behind 31 million writes", RED_M)], 2.4),
        ])
        self.stamp("singer")
        self.steps("That's the celebrity problem: one account with so many followers that its work holds up everyone else's.", [
            (lambda: [*self.cap("the celebrity problem: one account's work holds up everyone else's", YELLOW_M), glow(sg[0], GOLD_M)], 0.8),
        ])
        self.steps("In the mail room, one sender writes to 31 million people at once, and the clerks do nothing else all morning.", [
            "the clerks do nothing",
            (lambda: [dots(8), glow(ck[0], TEAL_M)], 2.0),
        ], after=0.5)

        # ---------------- scene 7: the moral ----------------
        self.steps("So the average told the wrong story. The average account has about 200 followers, and looks harmless. "
                   "The design is decided by the largest one.", [
            (lambda: self.cap("the average account: about 200 followers", WHITE), 0.6),
            "The design is",
            (lambda: [*self.cap("the design is decided by the largest one", GOLD_M), glow(sg[0], GOLD_M)], 0.8),
        ])
        self.steps("The cost of a post is its author's follower count. Find the largest one.", [
            (lambda: self.cap("the cost of a post is its author's follower count. find the largest one.", YELLOW_M, 26), 0.8),
        ], after=0.6)
        door = DashedVMobject(RoundedRectangle(corner_radius=0.1, width=3.7, height=0.6).set_stroke(GOLD_M, 2), num_dashes=46) \
            .move_to([-4.65, -2.55, 0])
        door_t = left_at(T("table by the door", 18, GOLD_M), -6.35, -2.55)
        self.steps("The fix comes next in the lesson: don't sort the giant's letters at all. "
                   "Leave them on a table by the door, and let each follower pick one up on the way out.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(bar_bg, bar, bar_l, clock))], 0.5),
            "Leave them",
            (lambda: [Create(door), FadeIn(door_t)], 0.8),
            (lambda: [s_post.animate.scale(0.85).move_to([-3.45, -2.55, 0])], 0.8),
            "let each follower",
            (lambda: [dot_to([-2.85, -2.55, 0], RD + [-RD_W / 2, -0.1, 0], GOLD_M, 1.0)], 1.1),
        ])

        # ---------------- scene 8: a check ----------------
        self.steps("One quick check. The café posts about today's cake. It has 300 followers. How many timeline writes is that? Pause and think.", [
            (lambda: [c_post[0].animate.set_stroke(TEAL_M), glow(c_post[0], TEAL_M, 1.1), *self.cap("the café, 300 followers: how many timeline writes?", WHITE)], 0.8),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("300, one per follower. That's cheap. It was late only because it waited behind the singer's 31 million.", [
            (lambda: [*self.cap("300: one per follower", GREEN_M, 28), c_post.animate.move_to(CK).set_opacity(0), FadeOut(cafe_fol)], 0.9),
            (lambda: [LaggedStart(*[dot_to(CK + [CK_W / 2, 0, 0], hole_c(r, c), TEAL_M, 0.5) for r, c in [(0, 1), (1, 3), (2, 0)]], lag_ratio=0.3)], 1.0),
            "It was late",
            (lambda: [glow(sg[0], GOLD_M)], 0.8),
        ], after=0.3)
        self.play(*self.cap("the cost of a post is its author's follower count. find the largest one.", YELLOW_M, 26), run_time=0.7)
        self.wait(2.0)
