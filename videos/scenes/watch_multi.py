from sfz import *

# How the narrator says the commands and names.
SAY[0:0] = [
    (r"\bbalance:7\b", "balance seven"),
    (r"\bMULTI\b", "multi"), (r"\bEXEC\b", "exec"), (r"\bWATCH\b", "watch"), (r"\bQUEUED\b", "queued"),
    (r"\bGETs\b", "gets"), (r"\bSETs\b", "sets"), (r"\bGET\b", "get"), (r"\bSET\b", "set"),
    # "pod A" alone reads as "pod uh"; "eh" lands on the letter.
    (r"\b[Pp]od A\b", lambda m: m.group(0)[0] + "od eh"),
]

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
BOX_TOP, BOX_BOT = 2.8, -0.9
BOX_CY = (BOX_TOP + BOX_BOT) / 2
POD_W = 4.0
PX = {"A": -4.6, "B": 4.6}                       # pod centres
WHO = {"A": BLUE_M, "B": GOLD_M}
RW = 3.6                                         # Redis in the middle
LY = [1.55 - 0.43 * i for i in range(6)]         # a pod's command lines
LINK_Y = 0.93
STRIP_Y, STRIP_LAB_Y = -1.85, -1.33              # the thread's order
BAR_Y, CAP_Y = -2.6, -3.2
VAL_Y = 0.93
WROW_Y = {"A": -0.25, "B": -0.62}                # the watch list inside Redis


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


def frame_box(cx, w, color):
    return RoundedRectangle(corner_radius=0.16, width=w, height=BOX_TOP - BOX_BOT, stroke_color=color,
                            stroke_width=3).set_fill(fillc(color), 1).move_to([cx, BOX_CY, 0])


def pod(p, what):
    cx = PX[p]
    return VGroup(frame_box(cx, POD_W, WHO[p]), T(f"pod {p}", 28, WHO[p]).move_to([cx, BOX_TOP - 0.36, 0]),
                  T(what, 19, GREY_B).move_to([cx, BOX_TOP - 0.76, 0]))


def redis_box():
    r = frame_box(0, RW, WHITE).set_fill(BLACK, 1)
    return r


def cmd_line(p, i, text, reply=None, rcolor=GREY_B):
    x0 = PX[p] - POD_W / 2 + 0.22
    g = VGroup(left_at(M(text, 16), x0, LY[i]))
    if reply:
        g.add(M("→ " + reply, 16, rcolor).next_to(g[0], RIGHT, buff=0.13))
    return g


def thought(p, i, text, color=GREY_B):
    x0 = PX[p] - POD_W / 2 + 0.22
    return left_at(T(text, 19, color, slant=ITALIC), x0, LY[i])


class WatchMulti(Base):
    """txn-06, section 2. A prepaid card with 100 pays 30 and 50 at once and ends at 50: a lost update between two
    commands, although Redis runs one command at a time. The one-barista café. MULTI/EXEC is one slip of orders that
    runs as one step, but a GET on the slip answers QUEUED, so it can't decide, and it never rolls back. WATCH is
    telling the barista to throw your slip away if anyone changes the card first: B's write marks A dirty, A's EXEC
    answers nil, A retries and writes 20. Check-and-set, optimistic; one connection; hot keys mean retries; a check."""

    # --- small state helpers: each returns animations and updates what is on screen ---
    def cap(self, s, color=GREY_B, size=24):
        new = T(s, size, color).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def set_val(self, s, color=WHITE):
        new = M(s, 46, color).move_to([0, VAL_Y, 0])
        old, self.val = self.val, new
        return [swap(old, new)]

    def line(self, p, m):
        """Put a command or thought on pod p's next empty line."""
        self.lines[p].append(m)
        return [FadeIn(m, shift=0.08 * RIGHT)]

    def clear(self, p):
        olds, self.lines[p] = self.lines[p], []
        return [FadeOut(m) for m in olds]

    def reply(self, p, i, text, color=GREY_B):
        """Add Redis's answer to pod p's line i."""
        g = self.lines[p][i]
        r = M("→ " + text, 16, color).next_to(g[0], RIGHT, buff=0.13)
        g.add(r)
        return [FadeIn(r, shift=0.08 * LEFT)]

    def go(self, p, color=YELLOW_M, back=False):
        """A dot runs from pod p to Redis (a command), or back (an answer)."""
        a, b = self.links[p].get_start(), self.links[p].get_end()
        if p == "B":
            a, b = b, a
        if back:
            a, b = b, a
        d = Dot(radius=0.08, color=color).move_to(a)
        return [Succession(FadeIn(d, run_time=0.05), d.animate(run_time=0.45, rate_func=smooth).move_to(b),
                           FadeOut(d, run_time=0.1))]

    def chip(self, p, text, color=None):
        t = M(text, 17, color or WHITE)
        r = RoundedRectangle(corner_radius=0.1, width=t.width + 0.34, height=0.48, stroke_color=WHO[p], stroke_width=2.5)
        r.set_fill(fillc(WHO[p]), 1)
        g = VGroup(r, t.move_to(r))
        x = -6.55 if not self.chips else self.chips[-1].get_right()[0] + 0.14
        left_at(g, x, STRIP_Y)
        self.chips.append(g)
        return [FadeIn(g, shift=0.1 * RIGHT)]

    def clear_chips(self):
        olds, self.chips = self.chips, []
        return [FadeOut(c) for c in olds]

    def wrow(self, p, state):
        """The watch list row for pod p: 'clean', 'dirty' or None (gone)."""
        new = None
        if state:
            c = GREEN_M if state == "clean" else RED_M
            new = VGroup(T(f"pod {p}", 20, WHO[p]), T(state, 20, c)).arrange(RIGHT, buff=0.35).move_to([0, WROW_Y[p], 0])
        old, self.wr[p] = self.wr[p], new
        if new is None:
            return [FadeOut(old)] if old is not None else []
        return [swap(old, new)]

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def construct(self):
        self.capm = self.val = None
        self.lines = {"A": [], "B": []}
        self.chips = []
        self.wr = {"A": None, "B": None}
        self.title_card("Where did the 30 go?", "one command at a time, and the gap between two commands")

        # ---------------- scene 1: the hook ----------------
        card = RoundedRectangle(corner_radius=0.2, width=3.4, height=2.1, stroke_color=WHITE, stroke_width=3).set_fill("#15191d", 1)
        card.move_to([0, 0.9, 0])
        card_t = T("prepaid card", 24, GREY_B).move_to([0, 1.6, 0])
        bal = M("100", 52).move_to([0, 0.75, 0])
        coffee = VGroup(T("coffee", 22, BLUE_M), M("-30", 30, BLUE_M)).arrange(DOWN, buff=0.15).move_to([-4.4, 0.9, 0])
        fuel = VGroup(T("fuel", 22, GOLD_M), M("-50", 30, GOLD_M)).arrange(DOWN, buff=0.15).move_to([4.4, 0.9, 0])
        same = T("at the same moment", 22, GREY_B).move_to([0, 2.6, 0])
        self.steps("A prepaid card has 100 on it. At the same moment, it pays 30 for a coffee and 50 for fuel.", [
            (lambda: [FadeIn(VGroup(card, card_t), shift=0.2 * UP)], 0.7),
            (lambda: [FadeIn(bal)], 0.4),
            "At the same",
            (lambda: [FadeIn(coffee, shift=0.2 * RIGHT), FadeIn(fuel, shift=0.2 * LEFT), FadeIn(same)], 0.8),
        ])
        should = VGroup(T("should be", 22, GREY_B), M("20", 36, GREEN_M)).arrange(RIGHT, buff=0.25).move_to([-2.6, -1.0, 0])
        says = VGroup(T("the card says", 22, GREY_B), M("50", 36, RED_M)).arrange(RIGHT, buff=0.25).move_to([2.6, -1.0, 0])
        self.steps("So 20 should be left. The card says 50. Somewhere, 30 just walked out the door.", [
            (lambda: [FadeIn(should, shift=0.1 * UP)], 0.6),
            "The card says",
            (lambda: [FadeIn(says, shift=0.1 * UP), Transform(bal, M("50", 52, RED_M).move_to(bal))], 0.7),
            "Somewhere",
            (lambda: [Indicate(says[1], color=RED_M, scale_factor=1.25)], 0.9),
        ])
        qm = T("?", 60, YELLOW_M).move_to([0, -2.3, 0])
        self.steps("And the program that keeps the balance runs one command at a time, so nothing ever runs at once. "
                   "How did money go missing? And how do we stop it?", [
            (lambda: self.cap("one command at a time"), 0.6),
            "How did money",
            (lambda: [FadeIn(qm, scale=0.6)], 0.6),
        ])

        # ---------------- scene 2: one barista, Redis, pods ----------------
        rb = redis_box()
        r_name = T("one barista", 28).move_to([0, BOX_TOP - 0.36, 0])
        r_sub = T("one drink at a time", 19, GREY_B).move_to([0, BOX_TOP - 0.76, 0])
        orders = [mbox_order(s) for s in ("latte", "tea", "mocha")]
        for k, o in enumerate(orders):
            o.move_to([-3.2 - 1.45 * k, VAL_Y, 0])
        self.steps("Picture a café with one barista. She makes one drink at a time, and never starts the next until it's handed over.", [
            (lambda: [FadeOut(VGroup(card, card_t, bal, coffee, fuel, same, should, says, qm)), *self.uncap()], 0.7),
            (lambda: [FadeIn(rb), FadeIn(r_name), FadeIn(r_sub)], 0.7),
            (lambda: [LaggedStart(*[FadeIn(o, shift=0.2 * RIGHT) for o in orders], lag_ratio=0.25)], 0.8),
            "one drink",
            *[st for k in range(3) for st in (
                (lambda k=k: [orders[k].animate.move_to([0, VAL_Y, 0]),
                              *[orders[j].animate.shift(1.45 * RIGHT) for j in range(k + 1, 3)]], 0.55),
                (lambda k=k: [FadeOut(orders[k], scale=0.5)], 0.3))],
        ])
        r_name2 = T("Redis", 28).move_to(r_name)
        r_sub2 = T("one thread", 19, GREY_B).move_to(r_sub)
        cmds = [mbox_order(c, mono=True) for c in ("GET", "SET", "GET")]
        for k, o in enumerate(cmds):
            o.move_to([-3.2 - 1.45 * k, VAL_Y, 0])
        self.steps("Redis, a program that keeps data in memory and answers short commands, works the same way. "
                   "One thread, a single line of work, runs every command to the end before it takes the next.", [
            "Redis, a program",
            (lambda: [swap(r_name, r_name2)], 0.6),
            "One thread",
            (lambda: [swap(r_sub, r_sub2), glow(rb, WHITE, 1.02)], 0.8),
            (lambda: [LaggedStart(*[FadeIn(o, shift=0.2 * RIGHT) for o in cmds], lag_ratio=0.25)], 0.7),
            "runs every",
            *[st for k in range(3) for st in (
                (lambda k=k: [cmds[k].animate.move_to([0, VAL_Y, 0]),
                              *[cmds[j].animate.shift(1.45 * RIGHT) for j in range(k + 1, 3)]], 0.5),
                (lambda k=k: [FadeOut(cmds[k], scale=0.5)], 0.25))],
        ])
        key = M("balance:7", 22, GREY_B).move_to([0, 1.52, 0])
        self.steps("Redis keeps each value under a name, called its key. The card's balance sits under the key balance:7.", [
            "under the key",
            (lambda: [FadeIn(key, shift=0.1 * DOWN)], 0.5),
            (lambda: self.set_val("100"), 0.5),
        ])
        pa, pb = pod("A", "coffee, 30"), pod("B", "fuel, 50")
        self.links = {
            "A": Line([PX["A"] + POD_W / 2, LINK_Y, 0], [-RW / 2, LINK_Y, 0], stroke_width=2.5, color=GREY_C),
            "B": Line([RW / 2, LINK_Y, 0], [PX["B"] - POD_W / 2, LINK_Y, 0], stroke_width=2.5, color=GREY_C),
        }
        self.steps("Big apps run several copies of their program, so payments keep flowing if one machine fails. "
                   "Call each copy a pod. The coffee reaches pod A, and the fuel reaches pod B.", [
            "Call each copy",
            (lambda: [FadeIn(pa[0]), FadeIn(pa[1]), FadeIn(pb[0]), FadeIn(pb[1]), Create(self.links["A"]), Create(self.links["B"])], 0.8),
            "The coffee",
            (lambda: [FadeIn(pa[2], shift=0.1 * DOWN)], 0.5),
            "the fuel",
            (lambda: [FadeIn(pb[2], shift=0.1 * DOWN)], 0.5),
        ])

        # ---------------- scene 3: the lost update ----------------
        order_lab = left_at(T("the thread's order", 19, GREY_B), -6.55, STRIP_LAB_Y)
        self.steps("Each pod does what looks right. GET the balance, check that it's enough, then SET the new one.", [
            (lambda: [FadeIn(order_lab)], 0.5),
            "GET the",
            (lambda: self.cap("GET the balance,  check it,  SET the new one", WHITE), 0.6),
        ])
        self.steps("Pod A reads the balance: 100. Pod B reads it too: 100.", [
            (lambda: [*self.uncap(), *self.line("A", cmd_line("A", 0, "GET balance:7")), *self.go("A")], 0.6),
            (lambda: [*self.chip("A", "A: GET"), *self.go("A", WHITE, back=True), *self.reply("A", 0, "100")], 0.55),
            "Pod B",
            (lambda: [*self.line("B", cmd_line("B", 0, "GET balance:7")), *self.go("B")], 0.6),
            (lambda: [*self.chip("B", "B: GET"), *self.go("B", WHITE, back=True), *self.reply("B", 0, "100")], 0.55),
        ])
        self.steps("Pod A works out 100 minus 30, and SETs 70. Pod B works out 100 minus 50, and SETs 50.", [
            (lambda: self.line("A", thought("A", 1, "100 - 30 = 70")), 0.5),
            "and SETs 70",
            (lambda: [*self.line("A", cmd_line("A", 2, "SET balance:7 70")), *self.go("A")], 0.55),
            (lambda: [*self.chip("A", "A: SET 70"), *self.set_val("70")], 0.45),
            "Pod B works",
            (lambda: self.line("B", thought("B", 1, "100 - 50 = 50")), 0.5),
            "and SETs 50",
            (lambda: [*self.line("B", cmd_line("B", 2, "SET balance:7 50")), *self.go("B")], 0.55),
            (lambda: [*self.chip("B", "B: SET 50"), *self.set_val("50", RED_M)], 0.45),
        ])
        self.steps("The card paid 80, and the balance says 50. The last SET won, and it never saw the first. "
                   "That's called a lost update.", [
            (lambda: self.cap("paid 80,  balance says 50", RED_M), 0.5),
            "The last SET",
            (lambda: [Indicate(self.chips[3], color=RED_M, scale_factor=1.1), self.chips[2].animate.set_opacity(0.3)], 0.9),
            "called a lost",
            (lambda: self.cap("a lost update: one write replaced another it never saw", RED_M), 0.6),
        ])
        gap = SurroundingRectangle(VGroup(self.chips[1]), color=YELLOW_M, buff=0.07, corner_radius=0.1)
        self.steps("Notice, every command ran alone. The thread did nothing wrong. "
                   "A decision took two commands, and between them, the thread served the other pod.", [
            (lambda: [*self.uncap(), self.chips[2].animate.set_opacity(1),
                      LaggedStart(*[glow(c[0], WHITE, 1.05) for c in self.chips], lag_ratio=0.2)], 1.2),
            "A decision took",
            (lambda: [Indicate(self.chips[0][1], color=BLUE_M), Indicate(self.chips[2][1], color=BLUE_M)], 0.8),
            "between them",
            (lambda: [Create(gap)], 0.6),
        ])
        self.steps("A real barista would notice someone asking about your card in the middle of your order. "
                   "Redis doesn't remember who asked what. It serves each command, and moves on.", [
            (lambda: self.cap("where the café picture stops working"), 0.5),
            "Redis doesn't",
            (lambda: self.cap("Redis serves each command alone, and doesn't remember who asked"), 0.5),
        ])

        # ---------------- scene 4: the batch, and its break ----------------
        self.steps("Wouldn't it be nice to hand over the whole thing in one go? Redis has a batch for that, "
                   "like one slip with all your orders on it.", [
            (lambda: [FadeOut(gap), *self.uncap(), *self.clear("A"), *self.clear("B"), *self.clear_chips(),
                      pb.animate.set_opacity(0.25), self.links["B"].animate.set_opacity(0.25)], 0.8),
            (lambda: self.set_val("100"), 0.5),
            "one slip",
            (lambda: self.cap("a batch: one slip of commands", WHITE), 0.5),
        ])
        slip = RoundedRectangle(corner_radius=0.08, width=POD_W - 0.24, height=0.43 * 3 + 0.18, stroke_color=YELLOW_M, stroke_width=2)
        slip.move_to([PX["A"], (LY[0] + LY[2]) / 2, 0])
        self.steps("MULTI says: start a slip. Every command after it answers QUEUED instead of running. "
                   "EXEC then runs the whole slip as one step. No other pod's command can land in the middle.", [
            "MULTI says",
            (lambda: [*self.line("A", cmd_line("A", 0, "MULTI")), Create(slip)], 0.6),
            "Every command",
            (lambda: [*self.line("A", cmd_line("A", 1, "SET balance:7 70")), *self.go("A")], 0.55),
            (lambda: [*self.go("A", WHITE, back=True), *self.reply("A", 1, "QUEUED", YELLOW_M)], 0.5),
            "EXEC then",
            (lambda: [*self.line("A", cmd_line("A", 2, "EXEC")), *self.go("A")], 0.55),
            (lambda: [*self.chip("A", "A: MULTI..EXEC"), glow(slip, YELLOW_M, 1.02), *self.go("A", WHITE, back=True),
                      *self.reply("A", 2, "1) OK"), *self.set_val("70")], 0.7),
            "No other",
            (lambda: [glow(self.chips[0][0], BLUE_M, 1.05)], 0.8),
        ])
        self.steps("So let's put the GET on the slip too. What does it answer? Pause and guess.", [
            (lambda: [*self.clear("A"), *self.clear_chips(), FadeOut(slip), *self.cap("back to 100, and a new slip"),
                      *self.set_val("100")], 0.5),
            (lambda: [*self.line("A", cmd_line("A", 0, "MULTI")), *self.line("A", cmd_line("A", 1, "GET balance:7"))], 0.6),
            (lambda: self.line("A", thought("A", 2, "enough for 30?")), 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("QUEUED. The balance comes back with all the other answers, after EXEC. That's too late to decide what to SET. "
                   "A batch runs together, but it can't decide.", [
            (lambda: [*self.uncap(), *self.go("A"), *self.reply("A", 1, "QUEUED", YELLOW_M)], 0.6),
            "after EXEC",
            (lambda: [*self.line("A", cmd_line("A", 3, "EXEC")), *self.go("A")], 0.5),
            (lambda: [*self.go("A", WHITE, back=True), *self.reply("A", 3, "1) 100")], 0.5),
            "too late",
            (lambda: [*self.line("A", thought("A", 4, "too late to decide", RED_M))], 0.5),
            "A batch runs",
            (lambda: self.cap("a batch runs together, but it can't decide", WHITE), 0.6),
        ])
        self.steps("And one more surprise. If a command on the slip fails while it runs, it fails alone, and the rest still run. "
                   "There's no rollback. A batch means nothing can interrupt it. It doesn't mean all or nothing.", [
            "fails alone",
            (lambda: self.cap("one command fails alone; the rest still run", WHITE), 0.5),
            "There's no rollback",
            (lambda: self.cap("no rollback: not all or nothing", RED_M), 0.5),
        ])

        # ---------------- scene 5: the watch list ----------------
        div = Line([-RW / 2 + 0.25, 0.4, 0], [RW / 2 - 0.25, 0.4, 0], stroke_width=1.5, color=GREY_D)
        wl = T("watch list", 19, GREY_B).move_to([0, 0.13, 0])
        self.steps("So the decision stays in your code. We just need to know "
                   "if anyone changed the card while we were thinking.", [
            (lambda: [*self.clear("A"), *self.uncap(), pb.animate.set_opacity(1), self.links["B"].animate.set_opacity(1)], 0.7),
            "We just need",
            (lambda: self.cap("did anyone change the card while we were thinking?", WHITE), 0.6),
        ])
        self.steps("Back to the café. You tell the barista: I'm keeping an eye on card 7. "
                   "If anyone changes it before my slip arrives, throw my slip away.", [
            "You tell",
            (lambda: self.cap("\"keep an eye on card 7 for me\"", YELLOW_M), 0.5),
            "If anyone",
            (lambda: self.cap("\"if it changes before my slip, throw my slip away\"", YELLOW_M), 0.5),
        ])
        self.steps("She keeps a little list of who is watching which card. "
                   "Whenever anyone writes card 7, she puts a mark next to every other name watching it.", [
            (lambda: [Create(div), FadeIn(wl, shift=0.1 * UP)], 0.6),
            "Whenever anyone",
            (lambda: self.cap("any write to card 7: a mark by every other watcher", WHITE), 0.5),
        ])
        self.steps("That's exactly what Redis does. The command is WATCH. The list lives inside Redis, one entry per connection. "
                   "And a name with a mark is what Redis calls dirty.", [
            "The command is",
            (lambda: self.cap("keep an eye on it = WATCH", WHITE), 0.5),
            "The list lives",
            (lambda: [glow(rb, WHITE, 1.02)], 0.8),
            "what Redis calls",
            (lambda: self.cap("a name with a mark = dirty", RED_M), 0.5),
        ])

        # ---------------- scene 6: the race, replayed with WATCH ----------------
        self.steps("Let's replay the race. Both pods WATCH balance:7, then GET it: 100. "
                   "Each decides in its own code. Pod A plans 70, pod B plans 50.", [
            (lambda: self.uncap(), 0.4),
            "Both pods",
            (lambda: [*self.line("A", cmd_line("A", 0, "WATCH balance:7")), *self.line("B", cmd_line("B", 0, "WATCH balance:7")),
                      *self.go("A"), *self.go("B")], 0.6),
            (lambda: [*self.wrow("A", "clean"), *self.wrow("B", "clean")], 0.5),
            "then GET",
            (lambda: [*self.line("A", cmd_line("A", 1, "GET balance:7")), *self.line("B", cmd_line("B", 1, "GET balance:7")),
                      *self.go("A"), *self.go("B")], 0.55),
            (lambda: [*self.reply("A", 1, "100"), *self.reply("B", 1, "100"), *self.chip("A", "A: WATCH, GET"),
                      *self.chip("B", "B: WATCH, GET")], 0.5),
            "Pod A plans",
            (lambda: self.line("A", thought("A", 2, "plan: write 70")), 0.4),
            "pod B plans",
            (lambda: self.line("B", thought("B", 2, "plan: write 50")), 0.4),
        ])
        self.steps("Pod B is quicker. MULTI, SET 50, EXEC. Its name has no mark, so the slip runs. The balance is 50.", [
            "MULTI",
            (lambda: [*self.line("B", cmd_line("B", 3, "MULTI")), *self.line("B", cmd_line("B", 4, "SET balance:7 50"))], 0.6),
            "EXEC",
            (lambda: [*self.line("B", cmd_line("B", 5, "EXEC")), *self.go("B")], 0.5),
            "no mark",
            (lambda: [Indicate(self.wr["B"][1], color=GREEN_M)], 0.6),
            "so the slip",
            (lambda: [*self.chip("B", "B: MULTI..EXEC"), *self.go("B", WHITE, back=True), *self.reply("B", 5, "OK", GREEN_M)], 0.5),
            "The balance",
            (lambda: self.set_val("50"), 0.5),
        ])
        self.steps("And because the card was written, Redis marks every other watcher. "
                   "Pod A is now dirty, and pod A doesn't know it yet.", [
            "marks every",
            (lambda: [*self.wrow("A", "dirty"), *self.wrow("B", None)], 0.6),
            "doesn't know",
            (lambda: [glow(pa[0], BLUE_M, 1.02)], 0.8),
        ])
        self.steps("Now pod A sends its slip: MULTI, SET 70, EXEC. Without the watch, this SET would wipe out B's payment. "
                   "What happens now? Pause and guess.", [
            "MULTI",
            (lambda: [*self.line("A", cmd_line("A", 3, "MULTI")), *self.line("A", cmd_line("A", 4, "SET balance:7 70"))], 0.6),
            "EXEC",
            (lambda: [*self.line("A", cmd_line("A", 5, "EXEC")), *self.go("A")], 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("EXEC checks the mark first. It finds it, throws the SET away, and answers nil, Redis's word for no value. "
                   "Nothing ran, and B's payment survives.", [
            (lambda: [*self.uncap(), Indicate(self.wr["A"][1], color=RED_M, scale_factor=1.2)], 0.8),
            "throws the SET",
            (lambda: [self.lines["A"][4].animate.set_opacity(0.25)], 0.5),
            "answers nil",
            (lambda: [*self.go("A", RED_M, back=True), *self.reply("A", 5, "nil", RED_M), *self.chip("A", "A: MULTI..EXEC", RED_M)], 0.6),
            "Nothing ran",
            (lambda: [*self.cap("nil: nothing ran", RED_M), Indicate(self.val, color=WHITE, scale_factor=1.15)], 0.8),
        ])
        self.steps("Nil means: you lost the race, start over. Pod A watches again, reads 50, checks that 30 still fits, and writes 20. "
                   "Nobody touched the card this time, so EXEC runs.", [
            (lambda: [*self.cap("nil means: you lost the race, start over", WHITE)], 0.5),
            "Pod A watches",
            (lambda: [*self.clear("A"), *self.clear("B"), *self.clear_chips(), *self.wrow("A", None), *self.uncap()], 0.5),
            (lambda: [*self.line("A", cmd_line("A", 0, "WATCH balance:7")), *self.go("A"), *self.wrow("A", "clean")], 0.5),
            "reads 50",
            (lambda: [*self.line("A", cmd_line("A", 1, "GET balance:7", "50")), *self.chip("A", "A: WATCH, GET")], 0.5),
            "checks that",
            (lambda: self.line("A", thought("A", 2, "50 - 30 = 20")), 0.5),
            "and writes 20",
            (lambda: [*self.line("A", cmd_line("A", 3, "MULTI")), *self.line("A", cmd_line("A", 4, "SET balance:7 20"))], 0.5),
            "so EXEC runs",
            (lambda: [*self.line("A", cmd_line("A", 5, "EXEC")), *self.go("A")], 0.5),
            (lambda: [*self.reply("A", 5, "OK", GREEN_M), *self.chip("A", "A: MULTI..EXEC", GREEN_M), *self.set_val("20", GREEN_M), *self.wrow("A", None)], 0.5),
        ])
        ok = tick(True, 0.2).move_to([1.25, VAL_Y, 0])
        self.steps("20. Both payments count. And notice, Redis never made anyone wait. It only refused a decision made from old news.", [
            (lambda: [Create(ok), *self.cap("100 - 50 - 30 = 20", GREEN_M)], 0.6),
            "Redis never",
            (lambda: self.cap("no waiting, no locks: a refused decision, and a retry", WHITE), 0.6),
        ])

        # ---------------- scene 7: the name ----------------
        self.steps("This pattern is called check and set. Read, decide, and write only if nothing changed since the read, "
                   "inside a loop that tries again.", [
            (lambda: self.cap("check-and-set: read, decide, write only if nothing changed", YELLOW_M), 0.6),
            "inside a loop",
            (lambda: [LaggedStart(*[Indicate(m, color=BLUE_M, scale_factor=1.06) for m in self.lines["A"]], lag_ratio=0.15)], 1.4),
        ])
        self.steps("It's optimistic: it bets that clashes are rare, and pays only when one happens.", [
            (lambda: self.cap("optimistic: pay only when a clash happens", YELLOW_M), 0.6),
        ])

        # ---------------- scene 8: guardrails ----------------
        self.steps("Two things keep it honest. First, a watch belongs to a connection, the open line between your program and Redis. "
                   "WATCH, MULTI and EXEC must travel on the same one.", [
            (lambda: [FadeOut(ok), *self.uncap()], 0.4),
            "a watch belongs",
            (lambda: [glow(self.links["A"], YELLOW_M, 1.0), *self.cap("1. a watch belongs to one connection", WHITE)], 0.8),
            "must travel",
            (lambda: [LaggedStart(*[st for k in (0, 3, 5) for st in self.go("A")], lag_ratio=0.3)], 1.2),
        ])
        self.steps("Second, every retry costs trips there and back. If fifty pods write the same card all day, "
                   "it turns into musical chairs. Most attempts lose, and each loss costs another round.", [
            (lambda: self.cap("2. every retry costs trips there and back", WHITE), 0.5),
            "fifty pods",
            (lambda: [LaggedStart(*[st for _ in range(4) for p in ("A", "B") for st in self.go(p)], lag_ratio=0.15)], 2.0),
            "Most attempts",
            (lambda: self.cap("a busy key: most attempts lose", RED_M), 0.5),
        ])
        self.steps("For a key that busy, send the whole decision to Redis as a script, which never needs to retry. That's next.", [
            (lambda: self.cap("a busy key: send the decision as a script (next)", WHITE), 0.6),
        ])

        # ---------------- scene 9: moral and a check ----------------
        self.steps("So where did the 30 go? Into the gap between two commands. The thread was never the problem.", [
            (lambda: self.cap("where did the 30 go?  into the gap between two commands", WHITE), 0.6),
        ])
        self.steps("A batch runs together, but can't decide. WATCH lets your code decide, "
                   "and refuses the write if the card changed while you were thinking.", [
            (lambda: self.cap("a batch can't decide.  WATCH lets you decide, and checks.", YELLOW_M), 0.6),
            "refuses the write",
            (lambda: [glow(rb, WHITE, 1.02)], 0.8),
        ], after=0.6)
        self.steps("One quick check. After pod A's WATCH, pod B sets balance:7 to 100, the value it already had. "
                   "Does pod A's EXEC run? Pause and think.", [
            (lambda: [*self.uncap(), *self.clear("A"), *self.clear_chips(), *self.set_val("100")], 0.6),
            (lambda: [*self.line("A", cmd_line("A", 0, "WATCH balance:7")), *self.wrow("A", "clean")], 0.5),
            "pod B sets",
            (lambda: [*self.line("B", cmd_line("B", 0, "SET balance:7 100")), *self.go("B")], 0.6),
            (lambda: [*self.set_val("100")], 0.4),
            "Does pod",
            (lambda: [*self.line("A", cmd_line("A", 1, "MULTI")), *self.line("A", cmd_line("A", 2, "SET balance:7 70")),
                      *self.line("A", cmd_line("A", 3, "EXEC"))], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("No. It answers nil. Redis doesn't compare values. Any write marks the watchers, even one that changes nothing.", [
            (lambda: [*self.uncap(), *self.wrow("A", "dirty")], 0.5),
            "It answers",
            (lambda: [*self.go("A", RED_M, back=True), *self.reply("A", 3, "nil", RED_M)], 0.6),
            "Any write",
            (lambda: self.cap("any write marks the watchers", YELLOW_M, 30), 0.6),
        ], after=0.3)
        self.wait(2.0)


def mbox_order(s, mono=False):
    t = (M if mono else T)(s, 20)
    r = RoundedRectangle(corner_radius=0.1, width=1.25, height=0.55, stroke_color=GREY_B, stroke_width=2).set_fill(BLACK, 1)
    return VGroup(r, t.move_to(r))
