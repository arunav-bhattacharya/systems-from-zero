from sfz import *

SAY.insert(0, (r"\b1\.16 million\b", "one point one six million"))
SAY.insert(0, (r"\b3\.5 seconds\b", "three and a half seconds"))
SAY.insert(0, (r"\bEli\b", "Ee-lie"))   # plain "Eli" comes out as "Ellie"

ROWS = [1.6, 0.5, -0.6]
AX, MX, RX = -5.0, -0.2, 5.0          # authors, stored lists, readers
LW, LH = 4.4, 0.78
BAND_A, BAND_B = -2.3, -3.05


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


def items_text(s, r):
    it = M(s, 22, YELLOW_M)
    return it.move_to(r.get_right() + LEFT * (0.24 + it.width / 2))


def lst(name, items, row, color=GREY_B):
    r = RoundedRectangle(corner_radius=0.12, width=LW, height=LH, stroke_color=color, stroke_width=2.5)
    r.set_fill(BLACK, opacity=1).move_to([MX, ROWS[row], 0])
    n = T(name, 24)
    n.move_to(r.get_left() + RIGHT * (0.24 + n.width / 2))
    return VGroup(r, n, items_text(items, r))


def person(name, color, row, x):
    return box(name, color, w=1.7, h=0.72, size=26).move_to([x, ROWS[row], 0])


def harrow(a, b, color=GREY_B):
    """Arrow from the right edge of a to the left edge of b."""
    return Arrow(a.get_right(), b.get_left(), buff=0.12, stroke_width=3, color=color, max_tip_length_to_length_ratio=0.12)


def counts(post, read, pc=WHITE, rc=WHITE):
    return VGroup(T(post, 30, pc).move_to([-3.4, BAND_A, 0]), T(read, 30, rc).move_to([3.4, BAND_A, 0]))


def set_items(l, s):
    return Transform(l[2], items_text(s, l[0]))


def dim(*ms):
    return [m.animate.set_opacity(0.3) for m in ms]


class HomeTimeline(Base):
    """found-04, section 2: fan-out on read, fan-out on write, and the celebrity who breaks the second."""

    def construct(self):
        self.title_card("The home timeline", "where the work goes when someone posts")

        ana, ben, eli = (person(n, BLUE_M, i, AX) for i, n in enumerate(["Ana", "Ben", "Eli"]))
        cleo = person("Cleo", TEAL_M, 1, RX)
        follows = T("follows Ana, Ben, Eli", 22, GREY_B).next_to(cleo, DOWN, buff=0.2)
        self.steps("A home timeline is the recent posts of everyone you follow. Cleo follows Ana, Ben and Eli.", [
            (lambda: [FadeIn(cleo, shift=0.2 * LEFT)], 1.0),
            "Cleo follows",
            (lambda: [LaggedStart(*[FadeIn(p, shift=0.2 * RIGHT) for p in (ana, ben, eli)], lag_ratio=0.3), FadeIn(follows)], 1.6),
        ])

        # ---- fan-out on read ---------------------------------------------------------------------------
        mode = chip("fan-out on read", BLUE_M, 26).move_to([0, 3.12, 0])
        head = T("each author's posts", 24, GREY_B).move_to([MX, 2.42, 0])
        posts = [lst("Ana's posts", "p3", 0), lst("Ben's posts", "p5", 1), lst("Eli's posts", "p6", 2)]
        w_ana = harrow(ana, posts[0], BLUE_M)
        c1 = counts("a post: 1 write", " ")
        self.steps("The simplest design stores each post once, in its author's own list. When Ana posts, that's one write.", [
            (lambda: [FadeIn(head), LaggedStart(*[FadeIn(l) for l in posts], lag_ratio=0.2)], 1.6),
            "When Ana",
            (lambda: [GrowArrow(w_ana)], 0.6),
            (lambda: [set_items(posts[0], "p7 p3"), FadeIn(c1[0], shift=0.15 * UP)], 0.8),
        ])

        reads = [Arrow(l[0].get_right(), cleo.get_left(), buff=0.12, stroke_width=3, color=TEAL_M,
                       max_tip_length_to_length_ratio=0.12) for l in posts]
        got = chip("p7 p6 p5", TEAL_M, 22, mono=True).move_to(follows)
        c2 = counts("a post: 1 write", "a read: 3 lookups")
        self.steps("When Cleo opens the app, the service reads all three lists and merges them: three lookups. "
                   "The work happens on every read, so this is called fan-out on read.", [
            "the service reads",
            (lambda: [LaggedStart(*[GrowArrow(a) for a in reads], lag_ratio=0.2)], 1.0),
            (lambda: [LaggedStart(*[travel(a, TEAL_M, 0.7) for a in reads], lag_ratio=0.15)], 1.0),
            (lambda: [FadeOut(follows), FadeIn(got, scale=1.2), FadeIn(c2[1], shift=0.15 * UP)], 0.8),
            "so this is",
            (lambda: [FadeIn(mode, shift=0.15 * DOWN)], 0.8),
        ])

        n1 = T("2 million reads a second × 200 lookups  =  400 million lookups a second", 26, RED_M).move_to([0, BAND_B, 0])
        self.steps("Say 10 million users are online, each following 200 accounts and refreshing every 5 seconds. "
                   "That's 2 million reads a second, and 400 million lookups.", [
            "That's 2 million",
            (lambda: [FadeIn(n1, shift=0.15 * UP)], 1.0),
        ])

        # ---- fan-out on write --------------------------------------------------------------------------
        mode2 = chip("fan-out on write", GREEN_M, 26).move_to([0, 3.12, 0])
        head2 = T("each reader's timeline", 24, GREY_B).move_to([MX, 2.42, 0])
        tl = [lst("Dan's timeline", "p5 p2", 0), lst("Cleo's timeline", "p7 p6 p5", 1), lst("Fay's timeline", "p6 p3", 2)]
        dan, fay = person("Dan", TEAL_M, 0, RX), person("Fay", TEAL_M, 2, RX)
        self.steps("Turn it around. Keep a ready-made timeline for every user, and do the work once, when a post arrives. This is fan-out on write.", [
            (lambda: [FadeOut(w_ana), *[FadeOut(a) for a in reads], FadeOut(got), FadeOut(c2[1]), FadeOut(c1[0]),
                      n1.animate.set_opacity(0.35), *dim(ben, eli), FadeOut(mode)], 1.0),
            "Keep a",
            (lambda: [*[FadeOut(l) for l in posts], FadeOut(head)], 0.6),
            (lambda: [FadeIn(head2), LaggedStart(*[FadeIn(l) for l in tl], lag_ratio=0.2),
                      FadeIn(dan, shift=0.2 * LEFT), FadeIn(fay, shift=0.2 * LEFT)], 1.2),
            "This is",
            (lambda: [FadeIn(mode2, shift=0.15 * DOWN)], 0.8),
        ])

        fans = [Arrow(ana.get_right(), l[0].get_left(), buff=0.12, stroke_width=3, color=BLUE_M, max_tip_length_to_length_ratio=0.12)
                for l in tl]
        c3 = counts("a post: 3 writes", " ")
        self.steps("Ana has three followers, so her new post goes into three timelines. That's three writes.", [
            "so her new post",
            (lambda: [LaggedStart(*[GrowArrow(a) for a in fans], lag_ratio=0.2)], 0.9),
            (lambda: [set_items(tl[0], "p8 p5 p2"), set_items(tl[1], "p8 p7 p6"), set_items(tl[2], "p8 p6 p3")], 0.8),
            "That's three",
            (lambda: [FadeIn(c3[0], shift=0.15 * UP)], 0.8),
        ])

        rd = [harrow(tl[i], p, TEAL_M) for i, p in enumerate((dan, cleo, fay))]
        c4 = counts("a post: 3 writes", "a read: 1 lookup")
        self.steps("Cleo's read is now one lookup, of a list that's already merged.", [
            (lambda: [GrowArrow(rd[1])], 0.6),
            (lambda: [travel(rd[1], TEAL_M, 0.7), FadeIn(c4[1], shift=0.15 * UP)], 0.9),
        ])

        n2 = T("5,800 posts a second × 200 followers  =  1.16 million writes a second", 26, GREEN_M).move_to([0, BAND_B, 0])
        self.steps("With the same numbers, 5,800 posts a second to 200 followers each is 1.16 million writes a second. "
                   "That's about 345 times less work.", [
            (lambda: [n1.animate.set_opacity(1)], 0.5),
            "With the same",
            (lambda: [FadeOut(n1, shift=0.15 * UP), FadeIn(n2, shift=0.15 * UP)], 1.0),
            "That's about",
            (lambda: [Indicate(n2, color=GREEN_M, scale_factor=1.05)], 1.0),
        ])
        self.steps("It wins because people read their timelines far more often than their friends post.", [
            (lambda: [GrowArrow(rd[0]), GrowArrow(rd[2])], 0.8),
            (lambda: [travel(rd[0], TEAL_M, 0.6), travel(rd[1], TEAL_M, 0.6), travel(rd[2], TEAL_M, 0.6)], 0.8),
            (lambda: [travel(rd[0], TEAL_M, 0.6), travel(rd[1], TEAL_M, 0.6), travel(rd[2], TEAL_M, 0.6)], 0.8),
        ])

        # ---- the celebrity -----------------------------------------------------------------------------
        star = person("Star", GOLD_M, 0, AX)
        star_l = T("31 million followers", 22, GOLD_M).next_to(star, UP, buff=0.18)
        more = T("+ 30,999,997 more timelines", 26, RED_M).move_to([MX, -1.68, 0])
        deck = VGroup(*[RoundedRectangle(corner_radius=0.12, width=LW, height=LH, stroke_color=RED_M, stroke_width=2)
                        .set_fill(BLACK, 1).move_to(tl[2][0].get_center() + k * np.array([0.09, -0.09, 0])) for k in (3, 2, 1)])
        deck.set_z_index(-1)
        c5 = counts("a post: 31,000,000 writes", " ", pc=RED_M)
        self.steps("Now the celebrity. In 2012 one Twitter account had 31 million followers. One post from it is 31 million writes.", [
            (lambda: [FadeOut(rd[0]), FadeOut(rd[1]), FadeOut(rd[2]), FadeOut(c3[0]), FadeOut(c4[1]), FadeOut(n2),
                      *[a.animate.set_color(GOLD_M) for a in fans], ReplacementTransform(ana, star), FadeIn(star_l)], 1.2),
            "One post",
            (lambda: [FadeIn(deck), FadeIn(more),
                      set_items(tl[0], "s1 p8 p5"), set_items(tl[1], "s1 p8 p7"), set_items(tl[2], "s1 p8 p6"),
                      FadeIn(c5[0], shift=0.15 * UP)], 1.2),
        ])

        x0, x1 = -3.6, 4.0
        track = Line([x0, BAND_A, 0], [x1, BAND_A, 0], stroke_width=10, color=GREY_D)
        secs = ValueTracker(0)
        fill = always_redraw(lambda: Line([x0, BAND_A, 0], [x0 + (x1 - x0) * max(secs.get_value(), 0.01) / 108, BAND_A, 0],
                                          stroke_width=10, color=RED_M))
        cache = {}

        def sec_text():
            s = f"{int(secs.get_value())} s"
            if s not in cache:
                cache[s] = T(s, 28, RED_M)
            return cache[s].copy().next_to(track, RIGHT, buff=0.3)
        secs_t = always_redraw(sec_text)
        gx = x0 + (x1 - x0) * 5 / 108
        goal = Line([gx, BAND_A - 0.28, 0], [gx, BAND_A + 0.28, 0], stroke_width=4, color=GREEN_M)
        goal_l = T("goal: 5 s", 24, GREEN_M).next_to(track, LEFT, buff=0.3)
        rate = T("Twitter's workers: a million followers every 3.5 s", 24, GREY_B).move_to([0, BAND_B, 0])
        self.steps("Twitter's workers reached a million followers in about 3.5 seconds. At that rate, this one post takes about 108 seconds. The goal was 5.", [
            (lambda: [FadeOut(c5[0]), Create(track), FadeIn(rate), FadeIn(goal), FadeIn(goal_l)], 0.9),
            "At that rate",
            (lambda: [FadeIn(fill), FadeIn(secs_t)], 0.2),
            (lambda: [secs.animate(rate_func=linear).set_value(108)], 3.0),
            "The goal",
            (lambda: [Indicate(goal_l, color=GREEN_M)], 0.9),
        ])

        qlab = T("queue:", 24, GREY_B)
        q = VGroup(qlab, chip("Star's post", GOLD_M, 22), chip("Ben's post", RED_M, 22), chip("Eli's post", RED_M, 22))
        q.arrange(RIGHT, buff=0.3).move_to([0, BAND_B, 0])
        wait_l = T("waiting", 24, RED_M).next_to(q, RIGHT, buff=0.3)
        self.steps("The workers take posts from a queue, so every ordinary post behind it waits too.", [
            (lambda: [FadeOut(rate)], 0.4),
            (lambda: [FadeIn(q[0]), FadeIn(q[1])], 0.6),
            "so every",
            (lambda: [FadeIn(q[2], shift=0.2 * LEFT), FadeIn(q[3], shift=0.2 * LEFT), FadeIn(wait_l),
                      ben.animate.set_opacity(1), eli.animate.set_opacity(1)], 1.0),
        ])

        # ---- the hybrid ---------------------------------------------------------------------------------
        mode3 = chip("hybrid", GOLD_M, 26).move_to([0, 3.12, 0])
        sp = lst("Star's posts", "s1", 0, GOLD_M)
        w_star = harrow(star, sp, GOLD_M)
        head3 = T("stored lists", 24, GREY_B).move_to([MX, 2.42, 0])
        fill.clear_updaters()
        secs_t.clear_updaters()
        c6 = counts("Star's post: 1 write", " ", pc=GOLD_M)
        self.steps("The fix is a hybrid. Accounts above a follower limit skip the fan-out. Their posts are stored once.", [
            (lambda: [FadeOut(track), FadeOut(fill), FadeOut(secs_t), FadeOut(goal), FadeOut(goal_l), FadeOut(q), FadeOut(wait_l),
                      ReplacementTransform(mode2, mode3), *dim(ben, eli)], 0.9),
            "skip the fan-out",
            (lambda: [*[FadeOut(a) for a in fans], FadeOut(deck), FadeOut(more),
                      set_items(tl[1], "p8 p7 p6"), set_items(tl[2], "p8 p6 p3")], 1.0),
            "Their posts",
            (lambda: [FadeOut(tl[0]), FadeOut(dan), FadeOut(head2)], 0.5),
            (lambda: [FadeIn(sp), FadeIn(head3), GrowArrow(w_star), FadeIn(c6[0], shift=0.15 * UP)], 0.9),
        ])

        r1 = Arrow(sp[0].get_right(), cleo.get_left(), buff=0.12, stroke_width=3, color=TEAL_M, max_tip_length_to_length_ratio=0.12)
        r2 = harrow(tl[1], cleo, TEAL_M)
        got2 = chip("s1 p8 p7", TEAL_M, 22, mono=True).next_to(cleo, DOWN, buff=0.2)
        c7 = counts("Star's post: 1 write", "Cleo's read: 2 lookups", pc=GOLD_M)
        self.steps("When Cleo reads, the service merges her timeline with the celebrity's list. Two lookups instead of one.", [
            (lambda: [GrowArrow(r1), GrowArrow(r2)], 0.8),
            (lambda: [travel(r1, TEAL_M, 0.7), travel(r2, TEAL_M, 0.7)], 0.8),
            (lambda: [FadeOut(fay), FadeOut(tl[2]), FadeIn(got2, scale=1.2)], 0.6),
            "Two lookups",
            (lambda: [FadeIn(c7[1], shift=0.15 * UP)], 0.8),
        ])

        self.steps("Precompute timelines for the many ordinary accounts. Merge in the few huge ones when someone reads.", [
            (lambda: [Indicate(tl[1][1], color=GREEN_M)], 1.2),
            "Merge in",
            (lambda: [Indicate(sp[1], color=GOLD_M)], 1.2),
        ])
        self.wait(0.6)
