from sfz import *

# A lone capital A (worker or server A) mid-sentence: Kokoro reads it as the article "uh". Sentence starts keep "A".
SAY.insert(0, (r"(^|[.!?]\s+)?\bA\b", lambda m: m.group(0) if m.group(1) is not None else "eh"))

SAY.insert(0, (r"\betcd\b", "et C D"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
SVW, SVH = 2.4, 0.95                                    # the three servers
A_C, B_C, C_C = np.array([-5.3, 0.6, 0]), np.array([-5.3, -1.2, 0]), np.array([-5.3, 2.5, 0])
LK_C, LK_W, LK_H, BARW = np.array([-1.3, 2.45, 0]), 4.0, 1.45, 2.4   # the Redis lock and its deadline bar
CT_C, CT_W, CT_H = np.array([4.3, 2.45, 0]), 3.0, 1.3   # the fence counter
ST_C, ST_W, ST_H = np.array([4.3, -0.3, 0]), 3.6, 2.4   # the payout store
CH_X = -1.3                                             # where a write appears
CODE_Y = -2.2
CAP_Y, BAR_Y = -3.25, -2.92


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

    def stamp(self, name):
        print(f"STAMP {name} {self.renderer.time:.1f}")

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def put(self, key, mob, d=UP):
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

    def gather(self, g):
        """Make a group of parts already on screen into one object on screen, so it can be transformed as a whole."""
        self.remove(*g.submobjects)
        self.add(g)
        return g

    def col(self, c):
        self.sil_col = c
        return [Wait(0.01)]

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



def panel(c, w, h, color, title, tsize=20):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1).move_to(c)
    return VGroup(r, T(title, tsize, GREY_B).move_to(c + np.array([0, h / 2 - 0.3, 0])))


def server(c, name, color):
    r = RoundedRectangle(corner_radius=0.14, width=SVW, height=SVH, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1).move_to(c)
    return VGroup(r, T(name, 24).move_to(r))


def wchip(s, color):
    t = M(s, 18, color)
    r = RoundedRectangle(corner_radius=0.1, width=t.width + 0.35, height=0.5, stroke_color=color, stroke_width=2).set_fill(BLACK, 1)
    return VGroup(r, t.move_to(r))


class FencingTokens(Base):
    """dist-05, section 3. The nightly payout file must be built once; three servers share a Redis lock with a
    10-second deadline. A takes it, freezes 15 s, the lock is deleted, B takes it and writes; A wakes and writes a file
    missing 12 shops. No check in A can catch it, so the store must refuse. The deli counter's tickets. Fencing tokens:
    33 for A, 34 for B; the store keeps the highest it has accepted (32, then 34) and refuses 33. Where the deli breaks
    (the store only learns of 34 when B writes). INCR in the lock script; UPDATE ... WHERE fence <= :t. Guardrails: a
    counter that never goes back, one Redis server, efficiency vs correctness. Moral, and a check (35)."""

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("A ticket the late holder can't use", "fencing tokens let the store refuse a late write")

        # ---------------- scene 1: the payout job ----------------
        sa, sb, sc = server(A_C, "server A", BLUE_M), server(B_C, "server B", GREEN_M), server(C_C, "server C", GREY_B)
        store = panel(ST_C, ST_W, ST_H, TEAL_M, "payout store")
        self.steps("Every night, the payments company pays each shop what it took that day. One job builds the payout file, "
                   "the list that tells the bank how much to send to each shop.", [
            "One job builds",
            (lambda: [FadeIn(store, shift=0.1 * LEFT)], 0.7),
        ])
        self.steps("It must run exactly once. Run it twice, and every shop is paid twice. "
                   "The job runs on three servers, so that one dying on the night doesn't stop the payouts.", [
            (lambda: [*self.cap("run it twice: every shop paid twice", RED_M)], 0.5),
            "three servers",
            (lambda: [FadeIn(sa, shift=0.1 * RIGHT), FadeIn(sb, shift=0.1 * RIGHT), FadeIn(sc, shift=0.1 * RIGHT)], 0.8),
        ])
        lock = panel(LK_C, LK_W, LK_H, GOLD_M, "the lock, in Redis")
        self.lk_hold = None
        self.dl = ValueTracker(0)
        bar = always_redraw(lambda: Rectangle(width=max(BARW * self.dl.get_value() / 10, 0.001), height=0.16, stroke_width=0)
                            .set_fill(GOLD_M, 0.9).move_to([LK_C[0] - BARW / 2 + BARW * self.dl.get_value() / 20, LK_C[1] - 0.42, 0]))

        def holder(s, color):
            new = T(s, 22, color).move_to(LK_C + np.array([0, -0.06, 0]))
            old, self.lk_hold = self.lk_hold, new
            return [swap(old, new)]

        self.steps("So, the tempting fix: a lock. Before it starts, a server takes a lock that only one may hold, and the others wait. "
                   "We keep it in Redis, a fast store that all three servers can reach.", [
            "a lock",
            (lambda: [FadeIn(lock, shift=0.1 * DOWN), *self.uncap()], 0.7),
            "We keep it",
            (lambda: [*holder("free", GREY_B)], 0.4),
        ])
        self.steps("Inside one program, nobody can take a lock away from you. But a lock shared by three servers has to run out, "
                   "or a dead holder would block the payouts forever. So this one is a lease, with a deadline: ten seconds.", [
            "has to run out",
            (lambda: [*self.cap("a shared lock must run out: a lease", WHITE)], 0.5),
            "ten seconds",
            (lambda: [FadeIn(bar), self.dl.animate.set_value(10), *self.put("dl", T("10 s", 16, GOLD_M).move_to(LK_C + np.array([BARW / 2 + 0.35, -0.42, 0])))], 0.8),
        ])
        self.dl.set_value(0)

        # ---------------- scene 2: the late write ----------------
        def req(src, ok):
            a = Arrow(src[0].get_corner(UR) + np.array([-0.4, 0, 0]), lock[0].get_bottom() + np.array([-0.6 if src is sa else 0.3, 0, 0]),
                      buff=0.08, stroke_width=2.5, color=GREEN_M if ok else RED_M, max_tip_length_to_length_ratio=0.12)
            return a

        r_a = req(sa, True)
        self.steps("Watch one night. Server A takes the lock. Server B tries, and is refused.", [
            "Server A takes",
            (lambda: [GrowArrow(r_a), *holder("held by A", BLUE_M), self.dl.animate.set_value(10),
                      *self.put("dl", T("10 s", 16, GOLD_M).move_to(LK_C + np.array([BARW / 2 + 0.35, -0.42, 0])))], 0.7),
            "Server B tries",
            (lambda: [*self.put("rb", req(sb, False)), FadeOut(r_a)], 0.5),
            (lambda: [*self.put("rbx", tick(False, 0.12).move_to(self.lab["rb"].get_center()))], 0.3),
        ])
        frz = T("frozen", 20, GREY_B).move_to(A_C + np.array([0, -SVH / 2 - 0.25, 0]))
        sw = ValueTracker(0)
        swn = always_redraw(lambda: T(f"{int(sw.get_value())} s", 18, GREY_B).move_to(A_C + np.array([SVW / 2 + 0.45, 0, 0])))
        self.steps("Then A's program freezes, for fifteen seconds, while it cleans up its memory. Every part of it stops, "
                   "including the part that would renew the lock.", [
            (lambda: [*self.drop("rb", "rbx")], 0.3),
            "freezes",
            (lambda: [sa[0].animate.set_stroke(GREY_D).set_fill(fillc(GREY_D)), sa[1].animate.set_opacity(0.4), FadeIn(frz), FadeIn(swn)], 0.6),
            "Every part",
            (lambda: [sw.animate(rate_func=linear).set_value(4), self.dl.animate(rate_func=linear).set_value(6),
                      *self.put("dl", T("6 s", 16, GOLD_M).move_to(LK_C + np.array([BARW / 2 + 0.35, -0.42, 0])))], 2.0),
        ])
        self.steps("After ten seconds, Redis deletes the lock, exactly as asked. B takes it.", [
            (lambda: [sw.animate(rate_func=linear).set_value(10), self.dl.animate(rate_func=linear).set_value(0), *self.drop("dl")], 1.6),
            "B takes it",
            (lambda: [*self.put("rb", req(sb, True)), *holder("held by B", GREEN_M), self.dl.animate.set_value(10)], 0.6),
        ])
        fileB = wchip("B: 4,210 payouts", GREEN_M).move_to([CH_X, B_C[1], 0])
        self.content = None

        def set_content(s, color):
            new = T(s, 20, color).move_to(ST_C + np.array([0, -0.15, 0]))
            old, self.content = self.content, new
            return [swap(old, new)]

        def to_store(chip, y):
            return chip.animate.move_to([ST_C[0] - ST_W / 2 - chip.width / 2 - 0.25, y, 0])

        self.steps("B builds the payout file, and writes it.", [
            (lambda: [*self.drop("rb"), FadeIn(fileB, shift=0.2 * RIGHT)], 0.6),
            (lambda: [to_store(fileB, B_C[1])], 0.7),
            (lambda: [FadeOut(fileB), *set_content("B: 4,210 payouts", GREEN_M)], 0.4),
        ])
        fileA = wchip("A: 4,198 payouts", BLUE_M).move_to([CH_X, A_C[1], 0])
        self.steps("Then A wakes up. It carries on from where it stopped, and writes its file: built before B's run, and missing 12 shops.", [
            (lambda: [sw.animate(rate_func=linear).set_value(15)], 1.0),
            "A wakes up",
            (lambda: [sa[0].animate.set_stroke(BLUE_M).set_fill(fillc(BLUE_M)), sa[1].animate.set_opacity(1), FadeOut(frz), FadeOut(swn)], 0.5),
            "writes its file",
            (lambda: [FadeIn(fileA, shift=0.2 * RIGHT)], 0.5),
            (lambda: [to_store(fileA, A_C[1])], 0.7),
            (lambda: [FadeOut(fileA), *set_content("A: 4,198 payouts", RED_M)], 0.4),
            "missing 12",
            (lambda: [*self.cap("the bank gets A's out-of-date file: 12 shops missing", RED_M)], 0.5),
        ])
        self.stamp("bad")
        self.steps("From A's side, it blinked. And no check inside A can catch this. We saw that the freeze can land after any check.", [
            (lambda: [*self.cap("no check inside A can catch it: the freeze can land after any check", WHITE)], 0.5),
        ])
        self.steps("So if A can't know it's late, someone else has to refuse its write. Who sees every write? Only the thing being written: the store.", [
            "Who sees every write",
            (lambda: [*self.uncap(), glow(store[0], TEAL_M)], 0.8),
            "the store",
            (lambda: [*self.cap("the one place that sees every write: the store", TEAL_M)], 0.5),
        ])

        # ---------------- scene 3: the deli counter ----------------
        tix = VGroup(chip("33", GOLD_M, 30, mono=True), chip("34", GOLD_M, 30, mono=True)).arrange(RIGHT, buff=0.6).move_to([CH_X, -0.3, 0])
        tix_l = T("deli tickets", 18, GREY_B).next_to(tix, UP, buff=0.25)
        self.steps("Picture the deli counter at a supermarket. You pull a ticket: 33. The next person pulls 34. "
                   "Once the counter has served 34, someone who turns up late holding 33 is sent away, however sure they are that it's their turn.", [
            (lambda: [*self.uncap(), FadeIn(tix_l), *self.cap("the deli counter: tickets 33, then 34", GOLD_M)], 0.5),
            "You pull",
            (lambda: [FadeIn(tix[0], shift=0.1 * UP)], 0.4),
            "The next person",
            (lambda: [FadeIn(tix[1], shift=0.1 * UP)], 0.4),
            "Once the counter",
            (lambda: [*self.cap("34 served: a late 33 is sent away", GOLD_M), Create(tick(True, 0.15).next_to(tix[1], DOWN, buff=0.2))], 0.5),
            "sent away",
            (lambda: [Create(tick(False, 0.15).next_to(tix[0], DOWN, buff=0.2))], 0.4),
        ])
        self.steps("Map it. The ticket is a number the lock hands out with each new holder. The counter is the store.", [
            "The ticket",
            (lambda: [*self.cap("ticket = a number from the lock;   counter = the store", WHITE)], 0.5),
        ])

        # ---------------- scene 4: tokens ----------------
        ctr = panel(CT_C, CT_W, CT_H, PURPLE_M, "fence counter")
        keep = [sa, sb, sc, store, lock, bar, self.lk_hold, self.content] + list(store) + list(lock) + list(sa) + list(sb) + list(sc)
        self.cnum = None

        def set_ctr(n):
            new = M(str(n), 34, PURPLE_M).move_to(CT_C + np.array([0, -0.15, 0]))
            old, self.cnum = self.cnum, new
            return [swap(old, new)]

        self.hi = None

        def set_hi(n, color=TEAL_M):
            new = T(f"highest fence: {n}", 20, color).move_to(ST_C + np.array([0, 0.4, 0]))
            old, self.hi = self.hi, new
            return [swap(old, new)]

        self.steps("Let's play the night again, with numbers. Next to the lock sits a counter. It's at 32. "
                   "The store remembers the highest number it has accepted: also 32.", [
            (lambda: [*[FadeOut(m) for m in self.mobjects if isinstance(m, VMobject) and m not in keep and m is not self.capm], *self.uncap(),
                      *holder("free", GREY_B), self.dl.animate.set_value(0), *set_content("file: none yet", GREY_B)], 0.6),
            "Next to the lock",
            (lambda: [FadeIn(ctr, shift=0.1 * DOWN), *set_ctr(32)], 0.7),
            "The store remembers",
            (lambda: [*set_hi(32)], 0.5),
        ])
        tokA = T("token 33", 18, BLUE_M).move_to(A_C + np.array([0, SVH / 2 + 0.25, 0]))
        tokB = T("token 34", 18, GREEN_M).move_to(B_C + np.array([0, SVH / 2 + 0.25, 0]))
        self.steps("Server A takes the lock, and in the same step the counter goes up by one. It holds token 33. "
                   "B's attempt is refused, and uses up no number.", [
            "Server A takes",
            (lambda: [*holder("held by A", BLUE_M), self.dl.animate.set_value(10), *set_ctr(33)], 0.6),
            "It holds token",
            (lambda: [FadeIn(tokA, shift=0.1 * DOWN)], 0.5),
            "B's attempt",
            (lambda: [*self.put("rb", req(sb, False))], 0.4),
            (lambda: [*self.put("rbx", tick(False, 0.12).move_to(self.lab["rb"].get_center()))], 0.3),
        ])
        self.steps("Server A freezes. Ten seconds later the lock is gone, and B takes it, with token 34.", [
            (lambda: [*self.drop("rb", "rbx"), sa[0].animate.set_stroke(GREY_D).set_fill(fillc(GREY_D)), sa[1].animate.set_opacity(0.4), FadeIn(frz)], 0.5),
            (lambda: [self.dl.animate(rate_func=linear).set_value(0)], 1.6),
            "B takes it",
            (lambda: [*holder("held by B", GREEN_M), self.dl.animate.set_value(10), *set_ctr(34), FadeIn(tokB, shift=0.1 * DOWN)], 0.6),
        ])
        fB = wchip("file, fence 34", GREEN_M).move_to([CH_X, B_C[1], 0])
        self.steps("B writes its file with fence 34. The store compares. 34 is at least the 32 it has seen, so it accepts, and now remembers 34.", [
            (lambda: [FadeIn(fB, shift=0.2 * RIGHT)], 0.5),
            (lambda: [to_store(fB, B_C[1])], 0.6),
            "it accepts",
            (lambda: [FadeOut(fB), *set_content("B: 4,210 payouts", GREEN_M), *self.cap("34 >= 32: accepted", GREEN_M)], 0.5),
            "remembers 34",
            (lambda: [*set_hi(34)], 0.5),
        ])
        fA = wchip("file, fence 33", BLUE_M).move_to([CH_X, A_C[1], 0])
        self.steps("Now A wakes up and writes its file, with fence 33. What does the store do? Pause and guess.", [
            (lambda: [*self.uncap(), sa[0].animate.set_stroke(BLUE_M).set_fill(fillc(BLUE_M)), sa[1].animate.set_opacity(1), FadeOut(frz)], 0.5),
            "writes its file",
            (lambda: [FadeIn(fA, shift=0.2 * RIGHT)], 0.5),
            (lambda: [to_store(fA, A_C[1])], 0.6),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        nope = tick(False, 0.16).move_to(fA.get_center())
        self.steps("It refuses. 33 is below the 34 it already accepted. B's file stays.", [
            (lambda: [*self.cap("33 < 34: refused", RED_M), Create(nope)], 0.5),
            (lambda: [FadeOut(fA), FadeOut(nope)], 0.6),
            "B's file stays",
            (lambda: [Indicate(self.content, color=GREEN_M)], 0.7),
        ])
        self.stamp("refused")
        self.steps("However sure A is that it's its turn. That number is called a fencing token: it fences out every holder older than the newest writer.", [
            "called a fencing token",
            (lambda: [*self.cap("fencing token: a number that grows with every new holder", WHITE)], 0.5),
        ])
        self.steps("Here the deli picture breaks. The deli calls each number itself, so it knows when 34 is being served. "
                   "The store learns about 34 only when B writes. Had A woken up before that, its 33 would have been accepted.", [
            (lambda: [*self.cap("the store learns about 34 only when B writes", GOLD_M)], 0.5),
            "Had A woken",
            (lambda: [*self.cap("before B's write, 33 is still the newest the store has seen", GOLD_M)], 0.5),
        ])
        self.steps("And that's fine. Fencing only refuses a holder once a newer one has written, which is exactly the case that does harm.", [
            (lambda: [*self.cap("refused once a newer holder has written: exactly the harmful case", WHITE)], 0.5),
        ])

        # ---------------- scene 5: how it's built ----------------
        self.steps("How is it built? In Redis, the counter is one command, increment, run in the same small script that takes the lock. "
                   "So a number is handed out exactly when a lock is.", [
            "one command",
            (lambda: [*self.cap("INCR fence:{settle}, in the same script as the lock", PURPLE_M), glow(ctr[0], PURPLE_M)], 0.6),
        ])
        code = VGroup(M("UPDATE payout_files SET content = :c, fence = :t", 18, WHITE),
                      M("WHERE batch = :b AND fence <= :t", 18, YELLOW_M)).arrange(DOWN, buff=0.14, aligned_edge=LEFT).move_to([0, CODE_Y, 0])
        self.steps("The store's side is the half people miss, because it isn't lock code at all. In a database table, the write gets one extra condition: "
                   "change the row only if its stored fence is no larger than mine. Zero rows changed means: you're a late holder.", [
            (lambda: [*self.uncap(), FadeIn(code[0])], 0.5),
            "one extra condition",
            (lambda: [FadeIn(code[1])], 0.5),
            "Zero rows",
            (lambda: [*self.cap("0 rows changed: you are a late holder", RED_M)], 0.5),
        ])

        # ---------------- scene 6: guardrails ----------------
        self.steps("Now the fine print. The counter must never go backwards, so it gets no deadline, "
                   "and it must live where it can't be thrown away when memory fills up.", [
            (lambda: [FadeOut(code), *self.cap("the counter: no deadline, never thrown away", PURPLE_M)], 0.5),
        ])
        self.steps("And it's only as safe as that one Redis server. If the server dies before its last increments were copied to its spare, "
                   "a new holder can get a number that was already handed out.", [
            "a new holder",
            (lambda: [*self.cap("a lost increment can hand out the same number twice", RED_M), glow(ctr[0], RED_M)], 0.6),
        ])
        self.steps("That's why the numbers are safer in etcd or ZooKeeper, two systems built so a group of servers agrees on every change, "
                   "and both already keep a number like this.", [
            (lambda: [*self.cap("safer: etcd or ZooKeeper, which already keep such a number", WHITE)], 0.5),
        ])
        self.steps("And ask one question about any lock. Is it for efficiency, so two servers don't waste the same work? A single Redis key will do. "
                   "Or is it for correctness, where a double run pays the shops twice? Then the store itself has to check.", [
            (lambda: [*self.cap("efficiency lock: one Redis key is enough", GREEN_M)], 0.5),
            "Or is it for correctness",
            (lambda: [*self.cap("correctness lock: the store must check (a fencing token, or a unique batch id)", YELLOW_M)], 0.5),
        ])

        # ---------------- scene 7: the moral, and a check ----------------
        self.steps("So, the moral. A lock keeps holders apart only while every lease is alive. "
                   "The token keeps them apart at the one place that sees every write.", [
            (lambda: [*self.cap("the lock: apart while leases live.   the token: apart where the writes land", YELLOW_M)], 0.6),
            "The token keeps",
            (lambda: [glow(store[0], TEAL_M)], 0.8),
        ], after=0.5)
        self.steps("One quick check. The store has accepted 34. A server shows up with token 35. Accept, or refuse? Pause and think.", [
            (lambda: [*self.uncap(), *self.put("t35", left_at(T("token 35", 18, YELLOW_M), C_C[0] + SVW / 2 + 0.2, C_C[1]))], 0.5),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Accept. 35 is newer than anything the store has seen. It's the next holder, and the store now remembers 35.", [
            (lambda: [*self.cap("35 >= 34: accepted", GREEN_M), *set_hi(35, YELLOW_M)], 0.6),
        ])
        self.wait(2.0)
