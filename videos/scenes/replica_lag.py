from sfz import *

# sfz says PostgreSQL as "postgres", which the voice reads as "POST-gurz"; spell the vowel out
SAY.insert(0, (r"\bPostgreSQL\b", "post-gress"))
SAY.insert(0, (r"\br1\b", "R one"))
SAY.insert(0, (r"\br2\b", "R two"))
SAY.insert(0, (r"\bpay-41\b", "pay forty-one"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
BW, BH = 3.8, 2.3
LD_C = np.array([-3.7, 1.5, 0])          # the leader: the clerk's notebook
FO_C = np.array([3.7, 1.5, 0])           # follower r1: a town's copy
B_TOP = LD_C[1] + BH / 2
TITLE_Y, SUB_Y, CELL_Y, POS_Y = B_TOP - 0.33, B_TOP - 0.7, LD_C[1] - 0.2, LD_C[1] - 0.78
PH_C, PH_W, PH_H = np.array([-5.35, -1.6, 0]), 1.6, 2.5
RT_C, RT_W, RT_H = np.array([0.2, -1.6, 0]), 2.9, 1.0
TOK_C = np.array([-2.5, -2.55, 0])
CMP_C = np.array([4.35, -1.6, 0])
CLOCK_C = np.array([0, 3.2, 0])
CAP_Y, BAR_Y = -3.25, -2.8


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


def mbody(c, color, w=BW, h=BH):
    return RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1).move_to(c)


def cell_pos(c, i):
    return np.array([c[0] + (i - 0.5) * 0.8, CELL_Y, 0])


def cell(c, i, color, filled=True):
    sq = RoundedRectangle(corner_radius=0.06, width=0.62, height=0.55, stroke_color=color, stroke_width=2.5).move_to(cell_pos(c, i))
    if filled:
        sq.set_fill(fillc(color, 0.4), 1)
        return VGroup(sq, M(str(i + 1), 22).move_to(sq))
    return VGroup(DashedVMobject(sq.set_stroke(GREY_D, 2), num_dashes=24))


def mk_arrow(a, b, color=GREY_B, sw=3):
    return Arrow(np.array(a, dtype=float), np.array(b, dtype=float), buff=0, stroke_width=sw, color=color,
                 max_tip_length_to_length_ratio=0.12)


def phone_body(c=PH_C):
    body = RoundedRectangle(corner_radius=0.22, width=PH_W, height=PH_H, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1).move_to(c)
    screen = RoundedRectangle(corner_radius=0.1, width=PH_W - 0.22, height=PH_H - 0.55, stroke_width=0).set_fill("#15191d", 1).move_to(c)
    slot = Line(c + [-0.2, PH_H / 2 - 0.14, 0], c + [0.2, PH_H / 2 - 0.14, 0], stroke_width=3, color=GREY_C)
    return VGroup(body, screen, slot, T("café app", 17, GREY_B).move_to(c + [0, 0.8, 0]), T("refunds", 19).move_to(c + [0, 0.35, 0]))


def ph_item(s, color, c=PH_C):
    if s.startswith("pay"):
        return VGroup(M("pay-41", 18, color), T("refund", 18, color)).arrange(DOWN, buff=0.1).move_to(c + [0, -0.35, 0])
    return T(s, 19, color).move_to(c + [0, -0.2, 0])


class ReplicaLag(Base):
    """repl-03, section 1. The café owner refunds pay-41, reloads, and sees no refund: the leader committed it at
    position 2 at 1,000 ms, and the 1,010 ms reload was read on follower r1, 300 ms behind at position 0. Two obvious
    fixes broken (all her reads on the leader; the leader for a minute, broken by a six-minute catch-up). The club's
    notebook: the clerk tells you your line, you write it on your hand, you check a town's last line. The token,
    the router's comparison, read-your-writes, its limit (the support agent), two costs, the commit that waits, the
    PostgreSQL check, the moral, and a check question."""

    def clock(self, s):
        return self.put("clock", chip(s, YELLOW_M, 24, mono=True).move_to(CLOCK_C))

    def fpos(self, s, color=WHITE):
        return self.put("fpos", fit(T(s, 22, color), BW - 0.4).move_to([FO_C[0], POS_Y, 0]))

    def lpos(self, s):
        return self.put("lpos", T(s, 22).move_to([LD_C[0], POS_Y, 0]))

    def item(self, s, color):
        return self.put("item", ph_item(s, color, self.ph_c))

    def tok(self, s, color=YELLOW_M):
        return self.put("tok", fit(chip(s, color, 20), 3.5).move_to(TOK_C))

    def cmp(self, s, color=WHITE):
        return self.put("cmp", M(s, 26, color).move_to(CMP_C))

    def rlabel(self, s):
        return self.put("rt", T(s, 22, GOLD_M).move_to(RT_C))

    def fcells(self, n):
        """Show follower r1 holding the first n log entries."""
        out = []
        for i in range(2):
            new = cell(FO_C, i, TEAL_M, filled=i < n)
            out += self.put(f"fc{i}", new)
        return out

    def construct(self):
        self.lab = {}
        self.ph_c = PH_C
        self.title_card("Where did my refund go?", "a follower that's behind, and the position you carry")

        # ---------------- scene 1: the refund that vanished ----------------
        S = 1.45
        hook_c = np.array([0, 0.1, 0])
        ph = phone_body(hook_c).scale(S)
        toast = chip("Refund sent", GREEN_M, 14).scale(S).move_to(hook_c + [0, -0.85 * S, 0])
        self.steps("Picture a café owner at closing time. A customer's coffee was charged twice, so she opens the payments app "
                   "on her phone and taps Refund.", [
            "she opens",
            (lambda: [FadeIn(ph, shift=0.2 * UP)], 0.8),
            "taps Refund",
            (lambda: [glow(ph[0], GOLD_M, 1.04)], 0.6),
        ])
        self.steps("The app says, refund sent. She reloads the page to check, and the refund isn't in the list.", [
            (lambda: [FadeIn(toast, scale=0.8)], 0.5),
            "She reloads",
            (lambda: [FadeOut(toast)], 0.4),
            "the refund isn't",
            (lambda: self.put("item", ph_item("(none)", RED_M, hook_c).scale(S).move_to(hook_c + [0, -0.2 * S, 0])), 0.5),
        ])
        qm = T("?", 64, YELLOW_M).move_to([0, 2.6, 0])
        self.steps("So she taps Refund again. Did the first refund vanish? And if it didn't, why couldn't she see it? Hold that question.", [
            (lambda: [glow(ph[0], GOLD_M, 1.04)], 0.6),
            "Did the first",
            (lambda: [FadeIn(qm, scale=0.6)], 0.6),
        ])

        # ---------------- scene 2: the notebook and its copies ----------------
        hook = VGroup(ph, self.lab["item"])
        ld, fo = mbody(LD_C, BLUE_M), mbody(FO_C, TEAL_M)
        ld_sub = T("the clerk's notebook", 19, GREY_B).move_to([LD_C[0], SUB_Y, 0])
        fo_sub = T("a town's copy", 19, GREY_B).move_to([FO_C[0], SUB_Y, 0])
        lcells = [cell(LD_C, i, BLUE_M) for i in range(2)]
        lag = mk_arrow([LD_C[0] + BW / 2 + 0.1, LD_C[1] + 0.1, 0], [FO_C[0] - BW / 2 - 0.1, LD_C[1] + 0.1, 0])
        lag_t = T("300 ms behind", 20, GREY_B).next_to(lag, UP, buff=0.15)

        def to_place():
            return [FadeOut(qm), hook.animate.scale(1 / S).move_to(PH_C)]

        self.steps("Picture a club's notebook. One clerk writes each change on the next numbered line. "
                   "Copies are posted to other towns, and each town's copy is right as of the last letter it got.", [
            (lambda: to_place(), 1.0),
            "One clerk",
            (lambda: [FadeIn(ld), FadeIn(ld_sub)], 0.6),
            "next numbered",
            (lambda: [LaggedStart(*[FadeIn(c, scale=0.7) for c in lcells], lag_ratio=0.5)], 0.8),
            "Copies are posted",
            (lambda: [FadeIn(fo), FadeIn(fo_sub), GrowArrow(lag), *self.fcells(0)], 0.8),
            "each town's copy",
            (lambda: [run(lag)], 0.6),
            (lambda: self.fcells(1), 0.3),
            (lambda: [run(lag)], 0.6),
            (lambda: self.fcells(2), 0.3),
        ])
        ld_t = T("leader", 26).move_to([LD_C[0], TITLE_Y, 0])
        fo_t = T("follower r1", 26).move_to([FO_C[0], TITLE_Y, 0])
        self.steps("The payments app works the same way. One computer, the leader, writes every change at the next position in its log, "
                   "a numbered list of changes. Other computers, the followers, copy that log in order, a little later.", [
            "the leader",
            (lambda: [FadeIn(ld_t, shift=0.1 * DOWN), *self.lpos("position 2")], 0.6),
            "a numbered list",
            (lambda: [LaggedStart(*[Indicate(c, color=BLUE_M, scale_factor=1.15) for c in lcells], lag_ratio=0.4)], 0.9),
            "the followers",
            (lambda: [FadeIn(fo_t, shift=0.1 * DOWN), *self.fpos("position 2")], 0.6),
            "a little later",
            (lambda: [run(lag, rt=1.0), FadeIn(lag_t)], 1.0),
        ])
        rt = mbody(RT_C, GOLD_M, RT_W, RT_H)
        a_in = mk_arrow([PH_C[0] + PH_W / 2 + 0.1, RT_C[1], 0], [RT_C[0] - RT_W / 2 - 0.1, RT_C[1], 0])
        a_fo = mk_arrow([RT_C[0] + 0.9, RT_C[1] + RT_H / 2 + 0.08, 0], [FO_C[0] - 0.6, LD_C[1] - BH / 2 - 0.1, 0])
        a_ld = mk_arrow([RT_C[0] - 0.9, RT_C[1] + RT_H / 2 + 0.08, 0], [LD_C[0] + 0.6, LD_C[1] - BH / 2 - 0.1, 0])
        self.steps("Most pages read from a follower, so the leader keeps its time for card payments. "
                   "And a read on a follower shows the data as of that follower's position.", [
            "Most pages",
            (lambda: [dot_run(a_in.get_start(), FO_C + [-0.6, -BH / 2, 0], WHITE, 0.9)], 0.9),
            "And a read",
            (lambda: [*self.cap("a read on a follower shows that follower's position", WHITE), glow(fo, TEAL_M, 1.02)], 0.9),
        ])

        # ---------------- scene 3: her evening on the clock ----------------
        refund = chip("refund pay-41", GOLD_M, 18, mono=True).move_to(LD_C + [0, BH / 2 + 0.4, 0])
        self.steps("Now let's put a clock on her evening. At 1,000 ms, she asks for a refund of pay-41. "
                   "The leader commits it, writes it for good, at position 2.", [
            (lambda: [*self.drop("cap"), *self.clock("1,000 ms"), *self.fcells(0), *self.fpos("position 0"),
                      lcells[1].animate.set_opacity(0.15), *self.lpos("position 1"), *self.drop("item")], 0.8),
            "she asks",
            (lambda: [FadeIn(refund, shift=0.2 * DOWN)], 0.6),
            "The leader commits",
            (lambda: [refund.animate.move_to(lcells[1]).scale(0.3).set_opacity(0), lcells[1][1].animate.set_opacity(1),
                      lcells[1][0].animate.set_fill(fillc(GOLD_M, 0.5), 1).set_stroke(GOLD_M, opacity=1)], 0.7),
            "at position 2",
            (lambda: self.lpos("position 2"), 0.4),
        ])
        self.steps("At 1,010 ms, her page reloads. A load balancer, a program that spreads reads across the followers, "
                   "sends the question to follower r1.", [
            (lambda: self.clock("1,010 ms"), 0.4),
            "A load balancer",
            (lambda: [FadeIn(rt), *self.rlabel("load balancer"), GrowArrow(a_in)], 0.8),
            "sends the question",
            (lambda: [GrowArrow(a_fo)], 0.5),
            (lambda: [run(a_in, WHITE)], 0.5),
            (lambda: [run(a_fo, WHITE)], 0.6),
        ])
        crawl = Dot(radius=0.09, color=GOLD_M).move_to(lag.get_start()).set_z_index(6)
        self.steps("r1 is 300 ms behind. It's still at position 0. So the refund list is empty, and she taps Refund again.", [
            (lambda: [Indicate(lag_t, color=WHITE), FadeIn(crawl)], 0.6),
            (lambda: [crawl.animate(rate_func=linear).move_to(lag.point_from_proportion(0.25))], 0.8),
            "still at position 0",
            (lambda: [glow(fo, TEAL_M, 1.02)], 0.6),
            "the refund list",
            (lambda: [*self.item("(none)", RED_M), crawl.animate(rate_func=linear).move_to(lag.point_from_proportion(0.4))], 0.6),
            "taps Refund again",
            (lambda: [glow(ph[0], GOLD_M, 1.04)], 0.6),
        ])
        self.steps("The database turns the second refund away as a repeat, so no money is lost. "
                   "But the screen was wrong, and her call to the support line is real.", [
            "turns the second",
            (lambda: self.cap("the second refund: turned away as a repeat"), 0.5),
            "But the screen",
            (lambda: [*self.cap("but the screen was wrong", RED_M), ph[0].animate.set_stroke(RED_M)], 0.6),
        ])
        self.steps("Her refund was safe the whole time. It was only in the post. "
                   "So the real question is: how can a page tell whether this copy has her change yet?", [
            "only in the post",
            (lambda: [crawl.animate(rate_func=linear).move_to(lag.point_from_proportion(0.55)), Indicate(lcells[1], color=GOLD_M)], 0.9),
            "So the real",
            (lambda: [*self.cap("does this copy have her change yet?", YELLOW_M), ph[0].animate.set_stroke(WHITE)], 0.6),
        ])

        # ---------------- scene 4: two obvious fixes ----------------
        self.steps("You might be thinking: send her reads to the leader. That's correct. But most pages show a shop owner's own data, "
                   "so soon the leader takes most reads again.", [
            (lambda: [FadeOut(crawl), *self.cap("1. every read of her own data: the leader", WHITE), FadeOut(a_fo), GrowArrow(a_ld)], 0.7),
            "That's correct",
            (lambda: [run(a_in, WHITE, 0.4)], 0.4),
            (lambda: [run(a_ld, WHITE, 0.5)], 0.5),
            (lambda: [*self.item("pay-41 refund", GREEN_M)], 0.4),
            "most reads again",
            (lambda: [LaggedStart(*[run(a_ld, WHITE, 0.5) for _ in range(6)], lag_ratio=0.25), glow(ld, RED_M, 1.02)], 1.6),
        ])
        self.steps("Here's a cleverer one. For one minute after each change she makes, read from the leader. "
                   "After that, a follower is surely caught up. Will this hold? Pause and guess.", [
            (lambda: [*self.cap("2. the leader for 1 minute after each change, then any follower", WHITE)], 0.6),
            "Will this hold",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("It passes every test, because on a quiet test computer, lag is a few milliseconds.", [
            (lambda: [*self.cap("on a test computer: lag of a few milliseconds"), *self.fcells(2), *self.fpos("position 2")], 0.6),
            (lambda: self.put("cmp", tick(True, 0.22).move_to(CMP_C)), 0.4),
        ])
        self.steps("Then one night a follower restarts and spends six minutes catching up. "
                   "For every owner who changed something in that window, the change vanishes.", [
            (lambda: [*self.drop("cmp"), *self.fcells(0), *self.fpos("restarting: 6 minutes to catch up", RED_M),
                      fo.animate.set_stroke(RED_M)], 0.7),
            "For every owner",
            (lambda: [*self.clock("1 minute later"), FadeOut(a_ld), GrowArrow(a_fo)], 0.6),
            (lambda: [run(a_in, WHITE, 0.4)], 0.4),
            (lambda: [run(a_fo, WHITE, 0.5)], 0.5),
            "the change vanishes",
            (lambda: self.item("(none)", RED_M), 0.5),
        ])
        self.steps("One minute was a guess about the clock. A timer is a promise the follower never signed.", [
            (lambda: self.cap("one minute: a guess about the clock", RED_M), 0.5),
            "A timer",
            (lambda: [Wiggle(self.lab["clock"], scale_value=1.1)], 0.9),
        ], after=0.5)

        # ---------------- scene 5: the number on your hand ----------------
        self.steps("Back to the club. When you send the clerk a change, she writes it on line 2 and tells you: line 2. "
                   "You write that on the back of your hand.", [
            (lambda: [*self.drop("cap", "clock"), fo.animate.set_stroke(TEAL_M), *self.fpos("position 0"), *self.drop("item"),
                      Indicate(ld_sub, color=WHITE)], 0.8),
            "she writes it",
            (lambda: [Indicate(lcells[1], color=GOLD_M)], 0.6),
            "on the back",
            (lambda: [dot_run(LD_C + [0, -BH / 2, 0], TOK_C, YELLOW_M, 0.8), *self.tok("on your hand: line 2")], 0.9),
        ])
        self.steps("Later you walk into a town's reading room. First, you look at its last line. Line 0? Your change hasn't arrived. "
                   "Wait a little, or go to the clerk's own notebook. Line 2 or later? Read right there.", [
            (lambda: [Indicate(fo_sub, color=WHITE), *self.rlabel("checks the last line")], 0.7),
            "you look at",
            (lambda: [run(a_fo, GOLD_M)], 0.6),
            "Line 0",
            (lambda: self.cmp("0 < 2"), 0.5),
            "go to the clerk",
            (lambda: [FadeOut(a_fo), GrowArrow(a_ld)], 0.6),
            "Line 2 or later",
            (lambda: self.cap("line 2 or later? read right there", WHITE), 0.5),
        ])
        self.steps("Now map it. The line number is the log position. The number on your hand is a token, kept in her session, "
                   "the app's memory of one signed-in user.", [
            (lambda: [*self.drop("cmp"), FadeOut(a_ld)], 0.4),
            "The line number",
            (lambda: [*self.cap("line number = log position", WHITE), Indicate(self.lab["lpos"], color=BLUE_M)], 0.7),
            "The number on",
            (lambda: [*self.tok("token: 2  (her session)"), *self.cap("the number on your hand = a token, in her session", WHITE)], 0.7),
        ])
        self.steps("And whoever checks the last line before you read is the router, the part of the app that picks a machine for each read.", [
            "is the router",
            (lambda: [*self.rlabel("router"), *self.cap("whoever checks = the router: it picks a machine for each read", WHITE)], 0.7),
        ])

        # ---------------- scene 6: replay it with the token ----------------
        self.steps("Let's replay her evening with the token. At 1,000 ms, the leader commits the refund at position 2 "
                   "and sends that position back. Her session keeps it: token 2.", [
            (lambda: [*self.drop("cap", "tok"), *self.clock("1,000 ms")], 0.6),
            "commits the refund",
            (lambda: [Indicate(lcells[1], color=GOLD_M)], 0.6),
            "sends that position",
            (lambda: [dot_run(LD_C + [0, -BH / 2, 0], TOK_C, YELLOW_M, 0.8)], 0.8),
            "Her session",
            (lambda: self.tok("token: 2"), 0.5),
        ])
        self.steps("At 1,010 ms, the page reloads. The router asks r1 for its position. r1 says 0. Where does this read go? Pause and guess.", [
            (lambda: self.clock("1,010 ms"), 0.4),
            "the page reloads",
            (lambda: [run(a_in, WHITE)], 0.6),
            "The router asks",
            (lambda: [GrowArrow(a_fo)], 0.4),
            (lambda: [run(a_fo, GOLD_M, 0.5)], 0.5),
            "r1 says",
            (lambda: [dot_run(a_fo.get_end(), a_fo.get_start(), TEAL_M, 0.5), *self.cmp("r1: 0 < 2")], 0.6),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("0 is below 2, so the read goes to the leader. The refund is listed. She doesn't tap again.", [
            (lambda: [*self.drop("cap"), FadeOut(a_fo), GrowArrow(a_ld)], 0.5),
            (lambda: [run(a_ld, WHITE)], 0.6),
            "The refund is",
            (lambda: [*self.item("pay-41 refund", GREEN_M), glow(ph[0], GREEN_M, 1.04)], 0.6),
        ], after=0.5)
        self.steps("At 1,300 ms, r1 has applied position 2. Now 2 is at or past 2, so her reads go back to r1. "
                   "The leader only took the reads that would have been wrong.", [
            (lambda: [*self.clock("1,300 ms"), run(lag, GOLD_M, 0.6)], 0.6),
            (lambda: [*self.fcells(2), *self.fpos("position 2")], 0.4),
            "Now 2",
            (lambda: [*self.cmp("r1: 2 ≥ 2", GREEN_M), FadeOut(a_ld), GrowArrow(a_fo)], 0.6),
            (lambda: [run(a_fo, WHITE)], 0.6),
            "The leader only",
            (lambda: [glow(ld, BLUE_M, 1.02)], 0.8),
        ])

        # ---------------- scene 7: the name ----------------
        self.steps("This promise has a name: read-your-writes. After you change something, your own reads always show the change.", [
            "read-your-writes",
            (lambda: self.cap("read-your-writes: your own reads show your own changes", YELLOW_M, 28), 0.7),
        ])
        self.steps("Notice what it doesn't promise. A support agent who changed nothing has token 0. "
                   "Every follower qualifies, so the agent may not see the refund yet. That's allowed.", [
            (lambda: [*self.drop("cap", "cmp"), *self.clock("1,010 ms"), *self.fcells(0), *self.fpos("position 0")], 0.6),
            "A support agent",
            (lambda: [*self.tok("support agent: token 0", GREY_B), *self.item("(none)", GREY_B)], 0.6),
            "Every follower",
            (lambda: [*self.cmp("r1: 0 ≥ 0"), run(a_fo, WHITE)], 0.7),
        ])
        self.play(*self.cap("it covers only your own changes", WHITE), run_time=0.5)
        self.wait(0.6)

        # ---------------- scene 8: two costs, one more option ----------------
        self.steps("Two costs come with the token. First, it must live where every one of her requests can find it. "
                   "A cookie, the small note a website keeps in one browser, works for one browser.", [
            (lambda: [*self.drop("cmp"), *self.clock("1,300 ms"), *self.tok("token: 2"), *self.item("pay-41 refund", GREEN_M),
                      *self.fcells(2), *self.fpos("position 2"), *self.cap("cost 1: every request must find the token", WHITE)], 0.7),
            "A cookie",
            (lambda: [*self.tok("cookie, in one browser: token 2")], 0.6),
        ])
        self.steps("But she refunds on her phone and checks on her laptop. So the server keeps the token, under her account.", [
            "checks on her laptop",
            (lambda: [*self.tok("on the laptop: no token", RED_M)], 0.6),
            "So the server",
            (lambda: [*self.tok("kept by the server")], 0.6),
        ])
        self.steps("Second, a follower that's paused or broken may never catch up. Don't let a read wait forever. "
                   "Wait a short time, then go to the leader.", [
            (lambda: [*self.cap("cost 2: a follower that never catches up", WHITE), *self.fpos("paused", RED_M),
                      fo.animate.set_stroke(RED_M), *self.fcells(1)], 0.7),
            "Wait a short time",
            (lambda: [*self.cmp("wait a little...")], 0.5),
            "then go to",
            (lambda: [*self.drop("cmp"), FadeOut(a_fo), GrowArrow(a_ld)], 0.5),
            (lambda: [run(a_ld, WHITE)], 0.6),
        ])
        self.steps("There's one more option: make every commit wait until a follower has applied it. "
                   "Every read is fresh, and every payment pays for it.", [
            (lambda: [*self.cap("one more option: every commit waits for a follower", WHITE), fo.animate.set_stroke(TEAL_M),
                      *self.fpos("position 2"), *self.fcells(2)], 0.7),
            "Every read is fresh",
            (lambda: [run(lag, GOLD_M, 0.5), dot_run(lag.get_end(), lag.get_start(), TEAL_M, 0.5)], 1.0),
            "every payment pays",
            (lambda: [glow(ld, RED_M, 1.02)], 0.8),
        ])
        veil = Rectangle(width=16, height=9, stroke_width=0).set_fill(BLACK, 0.86).set_z_index(8)
        code = VGroup(
            M("-- on the leader, right after the commit: the token", 22, GREY_B),
            M("SELECT pg_current_wal_lsn();", 30, BLUE_M),
            M("-- on the follower, before the read", 22, GREY_B),
            M("SELECT pg_last_wal_replay_lsn() >= token;", 30, TEAL_M),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        code[2].shift(0.3 * DOWN)
        code[3].shift(0.3 * DOWN)
        frame = SurroundingRectangle(code, buff=0.45, corner_radius=0.14, stroke_color=GREY_B, stroke_width=2).set_fill(BLACK, 1)
        card = VGroup(frame, code).move_to([0, 0.3, 0]).set_z_index(9)
        for m in card.get_family():
            m.set_z_index(9)
        self.steps("On PostgreSQL, a free database program, the token is the log position, read right after the commit. "
                   "The check on the follower is one comparison.", [
            (lambda: [*self.drop("cap"), FadeIn(veil), FadeIn(frame), FadeIn(code[0]), FadeIn(code[1])], 0.8),
            "The check",
            (lambda: [FadeIn(code[2]), FadeIn(code[3])], 0.6),
        ], after=1.2)
        self.play(FadeOut(card), FadeOut(veil), run_time=0.7)

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So, did her first refund vanish? No. It was on the leader all along. She read a copy that hadn't reached it.", [
            (lambda: [*self.cap("did her first refund vanish?", WHITE), FadeOut(a_ld)], 0.5),
            "on the leader",
            (lambda: [Indicate(lcells[1], color=GOLD_M), glow(ld, BLUE_M, 1.02)], 0.8),
            "She read a copy",
            (lambda: [*self.fcells(0), *self.fpos("position 0"), glow(fo, TEAL_M, 1.02)], 0.7),
        ])
        self.steps("The fix is to carry her last write's position, and refuse to read below it. Compare positions, not clocks.", [
            (lambda: [*self.cap("carry the position, and refuse to read below it", YELLOW_M, 28), *self.tok("token: 2")], 0.6),
            "Compare positions",
            (lambda: [*self.cap("compare positions, not clocks", YELLOW_M, 32), *self.drop("clock")], 0.6),
        ], after=0.6)
        fo_t2 = T("follower r2", 26).move_to(fo_t)
        self.steps("One quick check. Her token is 5. Follower r2 is at position 7. Where can her read go? Pause and think.", [
            (lambda: [*self.drop("cap", "item"), *self.tok("token: 5")], 0.5),
            "Follower r2",
            (lambda: [swap(fo_t, fo_t2), *self.drop("fc0", "fc1"), *self.fpos("position 7")], 0.7),
            "Where can",
            (lambda: [GrowArrow(a_ld), GrowArrow(a_fo)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("To r2. 7 is past 5, so her change is already there.", [
            (lambda: [*self.drop("cap"), *self.cmp("r2: 7 ≥ 5", GREEN_M), FadeOut(a_ld), a_fo.animate.set_color(GREEN_M)], 0.6),
            (lambda: [run(a_in, WHITE, 0.4)], 0.4),
            (lambda: [run(a_fo, GREEN_M, 0.5)], 0.5),
        ], after=0.3)
        self.play(*self.cap("compare positions, not clocks", YELLOW_M, 32), run_time=0.6)
        self.wait(2.0)
