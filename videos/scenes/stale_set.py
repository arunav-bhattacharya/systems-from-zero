from sfz import *

SAY.insert(0, (r"\bm-17\b", "M seventeen"))
SAY.insert(0, (r"\b([Rr])eader A\b", r"\1eader eh"))   # a capital A naming a reader is read as the article "uh"

A_C, W_C, B_C = BLUE_M, GOLD_M, TEAL_M
RC, OC = np.array([0, 1.45, 0]), np.array([0, -1.05, 0])     # Redis and Oracle centres
LOG_Y = -2.45


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


def store(title, c, w, h, color):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=2.5)
    r.set_fill(BLACK, opacity=1).move_to(c)
    t = T(title, 24, GREY_B).move_to(c + UP * (h / 2 - 0.32))
    return VGroup(r, t)


def val(s, y, color=WHITE, size=28):
    return T(s, size, color).move_to([0, y, 0])


def log_row(chips):
    g = VGroup(*chips).arrange(RIGHT, buff=0.16)
    return g.move_to([0, LOG_Y, 0])


def entry(s, color):
    return chip(s, color, 20)


def status(s, color):
    return T(s, 22, color)


class StaleSet(Base):
    """cache-07, section 1: the stale-set race (two readers, one writer, an old value written back after the delete),
    then a lease that refuses the late fill."""

    def construct(self):
        self.title_card("The stale set", "how a cache ends up with the old row, and how a lease stops it")

        redis = store("Redis, the cache", RC, 5.2, 1.7, RED_M)
        ora = store("Oracle, the database", OC, 5.2, 1.3, GREY_B)
        rv = val("m-17:  empty", RC[1] - 0.05, GREY_B)
        ov = val("m-17:  v1  Fietsen Utrecht", OC[1] - 0.17)
        self.steps("A payments service keeps merchant names in Oracle, and copies of them in Redis, a cache in memory.", [
            (lambda: [FadeIn(ora), FadeIn(ov)], 1.0),
            "and copies",
            (lambda: [FadeIn(redis), FadeIn(rv)], 1.0),
        ])

        mode = chip("rule: commit, then delete the cached copy", GREY_B, 24).move_to([0, 3.15, 0])
        self.steps("The rule so far: commit to the database, then delete the cached copy.", [
            (lambda: [FadeIn(mode, shift=0.15 * DOWN)], 1.0),
        ])

        # ---- the race -----------------------------------------------------------------------------------
        ra = box("reader A", A_C, w=2.4, h=0.75, size=26).move_to([-5.0, 0.2, 0])
        ra_l = T("fraud check", 20, GREY_B).next_to(ra, UP, buff=0.15)
        wr = box("writer", W_C, w=2.4, h=0.75, size=26).move_to([5.0, OC[1], 0])
        rb = box("reader B", B_C, w=2.4, h=0.75, size=26).move_to([5.0, 2.25, 0])

        def a_to_redis(color=A_C):
            return Arrow(ra.get_corner(UR) + 0.1 * DOWN, redis[0].get_left() + 0.25 * DOWN, buff=0.12, stroke_width=3,
                         color=color, max_tip_length_to_length_ratio=0.15)

        def a_to_ora():
            return Arrow(ra.get_corner(DR) + 0.1 * UP, ora[0].get_left(), buff=0.12, stroke_width=3, color=A_C,
                         max_tip_length_to_length_ratio=0.15)

        def w_to_ora():
            return Arrow(wr.get_left(), ora[0].get_right(), buff=0.12, stroke_width=3, color=W_C, max_tip_length_to_length_ratio=0.15)

        def w_to_redis():
            return Arrow(wr.get_corner(UL) + 0.35 * RIGHT, redis[0].get_right() + 0.35 * DOWN, buff=0.12, stroke_width=3,
                         color=W_C, max_tip_length_to_length_ratio=0.15)

        def b_to_redis(color=B_C):
            return Arrow(rb.get_left(), redis[0].get_right() + 0.5 * UP, buff=0.12, stroke_width=3, color=color,
                         max_tip_length_to_length_ratio=0.15)

        def back(ar, color):
            return travel(Line(ar.get_end(), ar.get_start()), color, 0.7)

        log = [entry("A: miss", A_C), entry("A: reads v1", A_C), entry("writer: commits v2", W_C),
               entry("writer: deletes", W_C), entry("A: stores v1", RED_M), entry("B: gets v1", RED_M)]
        log_row(log)
        ar1 = a_to_redis()
        self.steps("That rule still has a hole. Reader A, a fraud check, asks Redis for merchant m-17. Redis has nothing for it, so it misses.", [
            "Reader A",
            (lambda: [FadeIn(ra, shift=0.2 * RIGHT), FadeIn(ra_l)], 0.8),
            "asks Redis",
            (lambda: [GrowArrow(ar1)], 0.6),
            (lambda: [travel(ar1, A_C, 0.6)], 0.6),
            "it misses",
            (lambda: [back(ar1, GREY_B), Indicate(rv, color=GREY_B), FadeIn(log[0], shift=0.15 * UP)], 0.9),
        ])

        ar2 = a_to_ora()
        holds = chip("holds v1", A_C, 22).next_to(ra, DOWN, buff=0.25)
        paused = T("paused", 22, RED_M).next_to(holds, DOWN, buff=0.15)
        self.steps("It reads the row from Oracle: version 1, with the old name. Then it stalls before storing it, say in a garbage collection pause.", [
            (lambda: [FadeOut(ar1), GrowArrow(ar2)], 0.7),
            (lambda: [travel(ar2, A_C, 0.6)], 0.6),
            (lambda: [back(ar2, A_C), FadeIn(holds, shift=0.15 * DOWN), FadeIn(log[1], shift=0.15 * UP)], 0.9),
            "Then it stalls",
            (lambda: [FadeOut(ar2), ra[0].animate.set_stroke(GREY_D), ra[1].animate.set_color(GREY_C), FadeIn(paused)], 0.8),
        ])

        wa1 = w_to_ora()
        self.steps("Meanwhile, the writer renames the merchant and commits version 2.", [
            (lambda: [FadeIn(wr, shift=0.2 * LEFT)], 0.7),
            (lambda: [GrowArrow(wa1)], 0.6),
            (lambda: [travel(wa1, W_C, 0.6)], 0.6),
            (lambda: [Transform(ov, val("m-17:  v2  Velo Utrecht", OC[1] - 0.17, GREEN_M)), FadeIn(log[2], shift=0.15 * UP)], 0.8),
        ])

        wa2 = w_to_redis()
        self.steps("Then it deletes the cached copy, as the rule says. There's nothing there yet, so the delete removes nothing.", [
            (lambda: [FadeOut(wa1), GrowArrow(wa2)], 0.7),
            (lambda: [travel(wa2, W_C, 0.6)], 0.6),
            (lambda: [FadeIn(log[3], shift=0.15 * UP)], 0.6),
            "There's nothing",
            (lambda: [Indicate(rv, color=W_C)], 1.0),
        ])

        ar3 = a_to_redis(RED_M)
        self.steps("Now reader A's pause ends, and it stores what it read: version 1, kept for an hour.", [
            (lambda: [FadeOut(wa2), FadeOut(paused), ra[0].animate.set_stroke(A_C), ra[1].animate.set_color(WHITE)], 0.7),
            "and it stores",
            (lambda: [GrowArrow(ar3)], 0.6),
            (lambda: [travel(ar3, RED_M, 0.6)], 0.6),
            (lambda: [Transform(rv, val("m-17:  v1  Fietsen Utrecht", RC[1] - 0.05, RED_M)), FadeIn(log[4], shift=0.15 * UP)], 0.8),
        ])

        ttl = val("kept for 1 hour", RC[1] - 0.5, GREY_B, 22)
        br = b_to_redis(RED_M)
        got = chip("Fietsen Utrecht", RED_M, 22).next_to(rb, DOWN, buff=0.25)
        self.steps("Reader B asks for the merchant and gets the old name. So does every request for the next hour, and no write is coming to delete it.", [
            (lambda: [FadeOut(ar3), FadeOut(holds), FadeIn(ttl), FadeIn(rb, shift=0.2 * LEFT)], 0.8),
            (lambda: [GrowArrow(br)], 0.6),
            (lambda: [back(br, RED_M), FadeIn(got, shift=0.15 * DOWN), FadeIn(log[5], shift=0.15 * UP)], 0.9),
        ])

        x0 = log[1].get_left()[0]
        x1 = log[4].get_right()[0]
        yb = LOG_Y - 0.45
        brk = VGroup(Line([x0, yb, 0], [x1, yb, 0]), Line([x0, yb, 0], [x0, yb + 0.12, 0]), Line([x1, yb, 0], [x1, yb + 0.12, 0]))
        brk.set_stroke(RED_M, 3)
        brk_l = T("the race window", 22, RED_M).move_to([(x0 + x1) / 2, yb - 0.3, 0])
        self.steps("This is a stale set. Reader A's read came before the commit, and its write to the cache came after the delete.", [
            (lambda: [Create(brk), FadeIn(brk_l)], 1.0),
            "Reader A's read",
            (lambda: [Indicate(log[1], color=YELLOW_M, scale_factor=1.0), Indicate(log[2], color=YELLOW_M, scale_factor=1.0)], 1.2),
            "and its write",
            (lambda: [Indicate(log[3], color=YELLOW_M, scale_factor=1.0), Indicate(log[4], color=YELLOW_M, scale_factor=1.0)], 1.2),
        ])
        self.steps("The race is rare per request. When Meta measured, about one cache write in a million was still wrong five minutes later.", [
            (lambda: [Indicate(brk_l, color=RED_M)], 1.0),
        ])

        # ---- the lease ----------------------------------------------------------------------------------
        mode2 = chip("fix: a lease on every miss", GREEN_M, 24).move_to([0, 3.15, 0])
        self.steps("Redis forgot the delete, because deleting an empty key leaves no trace. The fix gives the delete something to cancel.", [
            (lambda: [FadeOut(VGroup(*log)), FadeOut(brk), FadeOut(brk_l), FadeOut(got), FadeOut(br), FadeOut(ttl),
                      Transform(rv, val("m-17:  empty", RC[1] - 0.05, GREY_B)),
                      Transform(ov, val("m-17:  v1  Fietsen Utrecht", OC[1] - 0.17)),
                      rb.animate.set_opacity(0.3), wr.animate.set_opacity(0.3)], 1.2),
            "The fix",
            (lambda: [ReplacementTransform(mode, mode2)], 0.8),
        ])

        log2 = [entry("A: lease 81", A_C), entry("A: reads v1", A_C), entry("writer: commits v2", W_C),
                entry("writer: deletes both", W_C), entry("A: fill refused", GREEN_M), entry("B: fills v2", GREEN_M)]
        log_row(log2)
        lease = val("lease m-17:  token 81", RC[1] - 0.5, A_C, 22)
        tok = chip("token 81", A_C, 22).next_to(ra, DOWN, buff=0.25)
        ar4 = a_to_redis()
        self.steps("Run it again. On the miss, reader A also takes the key's lease: a random token, stored in Redis next to the key.", [
            (lambda: [GrowArrow(ar4)], 0.6),
            (lambda: [travel(ar4, A_C, 0.6)], 0.6),
            "a random token",
            (lambda: [FadeIn(lease, shift=0.1 * UP), back(ar4, A_C), FadeIn(tok, shift=0.15 * DOWN), FadeIn(log2[0], shift=0.15 * UP)], 1.0),
        ])

        ar5 = a_to_ora()
        wa3, wa4 = w_to_ora(), w_to_redis()
        paused2 = T("paused", 22, RED_M).next_to(tok, DOWN, buff=0.15)
        holds2 = chip("token 81, v1", A_C, 22).next_to(ra, DOWN, buff=0.25)
        self.steps("Reader A reads version 1, then stalls. The writer commits version 2, then deletes the value and the lease together.", [
            (lambda: [FadeOut(ar4), GrowArrow(ar5)], 0.5),
            (lambda: [back(ar5, A_C), Transform(tok, holds2), FadeIn(log2[1], shift=0.15 * UP)], 0.8),
            (lambda: [FadeOut(ar5), ra[0].animate.set_stroke(GREY_D), ra[1].animate.set_color(GREY_C), FadeIn(paused2),
                      wr.animate.set_opacity(1)], 0.6),
            "The writer",
            (lambda: [GrowArrow(wa3)], 0.5),
            (lambda: [Transform(ov, val("m-17:  v2  Velo Utrecht", OC[1] - 0.17, GREEN_M)), FadeIn(log2[2], shift=0.15 * UP)], 0.7),
            "then deletes",
            (lambda: [FadeOut(wa3), GrowArrow(wa4)], 0.5),
            (lambda: [travel(wa4, W_C, 0.5)], 0.5),
            (lambda: [FadeOut(lease), FadeIn(log2[3], shift=0.15 * UP)], 0.6),
        ])

        ar6 = a_to_redis(RED_M)
        no = tick(False, 0.2).move_to(ar6.get_center() + np.array([-0.45, 0.45, 0]))
        self.steps("Reader A's pause ends, and it tries to fill the key. A small script checks for its token and stores the value in one step. "
                   "The token is gone, so the fill is refused.", [
            (lambda: [FadeOut(wa4), FadeOut(paused2), ra[0].animate.set_stroke(A_C), ra[1].animate.set_color(WHITE)], 0.6),
            (lambda: [GrowArrow(ar6)], 0.6),
            (lambda: [travel(ar6, RED_M, 0.6)], 0.6),
            "The token is gone",
            (lambda: [Create(no), Indicate(rv, color=GREEN_M), FadeIn(log2[4], shift=0.15 * UP)], 1.0),
        ])

        br2 = b_to_redis()
        got2 = chip("Velo Utrecht", GREEN_M, 22).next_to(rb, DOWN, buff=0.25)
        self.steps("Reader B misses, takes its own lease, reads version 2, and fills the cache with the new name.", [
            (lambda: [FadeOut(ar6), FadeOut(no), FadeOut(tok), rb.animate.set_opacity(1)], 0.6),
            (lambda: [GrowArrow(br2)], 0.5),
            (lambda: [travel(br2, B_C, 0.6)], 0.6),
            "and fills",
            (lambda: [Transform(rv, val("m-17:  v2  Velo Utrecht", RC[1] - 0.05, GREEN_M)), FadeIn(got2, shift=0.15 * DOWN),
                      FadeIn(log2[5], shift=0.15 * UP)], 1.0),
        ])

        self.steps("Every write into the cache must hold the key's lease, and every delete takes the lease away.", [
            (lambda: [Indicate(log2[0], color=A_C, scale_factor=1.0)], 1.0),
            "and every delete",
            (lambda: [Indicate(log2[3], color=W_C, scale_factor=1.0), Indicate(log2[4], color=GREEN_M, scale_factor=1.0)], 1.2),
        ])
        self.wait(0.6)
