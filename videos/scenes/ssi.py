from sfz import *

# Amounts are said the way people say them; captions keep "75.00" and "-25.00".
SAY.insert(0, (r"\b(\d+)\.00\b", r"\1"))
SAY.insert(0, (r"-(\d+)\.00\b", r"minus \1"))
SAY.insert(0, (r"\bacct-17\b", "account seventeen"))
SAY.insert(0, (r"\bPostgreSQL\b", "post-gress"))
SAY.insert(0, (r"\bMySQL\b", "my S Q L"))
SAY.insert(0, (r"\bSIREAD\b", "S I read"))
SAY.insert(0, (r"\bSSI\b", "S S I"))
SAY.insert(0, (r"\b40001\b", "four zero zero zero one"))
SAY.insert(0, (r"\b9\.1\b", "nine point one"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
LX = -4.3                                   # the account's two cards
CARD_Y = [1.55, -0.05]
CARD_W, CARD_H = 3.8, 1.25
TOTAL_Y = -1.4
DIV_X = -1.75
GA, GB = np.array([1.3, 0.75, 0]), np.array([5.0, 0.75, 0])   # the two withdrawals in the "who comes first" graph
NODE_W, NODE_H = 2.3, 1.05
ST_X, ST_Y = 3.15, [-1.45, -2.15]
CAP_Y, BAR_Y = -3.25, -2.85


class Base(VoiceScene):
    def add_mobjects_from_animations(self, animations):
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
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


# ---- the pieces ----
def card(k):
    c = np.array([LX, CARD_Y[k], 0])
    r = RoundedRectangle(corner_radius=0.14, width=CARD_W, height=CARD_H, stroke_color=WHITE, stroke_width=3).set_fill("#101010", 1)
    r.move_to(c)
    t = T(f"card {k + 1}", 24).move_to(c + [-CARD_W / 2 + 0.75, 0.25, 0])
    return VGroup(r, t)


def card_val(k, s, color=WHITE):
    return M(s, 28, color).move_to([LX + 0.85, CARD_Y[k] + 0.25, 0])


def card_note(k, s, color=GREY_B):
    return T(s, 18, color).move_to([LX, CARD_Y[k] - 0.33, 0])


def node(c, name, sub, color):
    r = RoundedRectangle(corner_radius=0.14, width=NODE_W, height=NODE_H, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1)
    r.move_to(c)
    return VGroup(r, T(name, 26, color).move_to(c + [0, 0.2, 0]), T(sub, 18, GREY_B).move_to(c + [0, -0.25, 0]))


def edge(frm, to, up, color):
    """A curved arrow between the two nodes, above (up=True) or below."""
    dy = NODE_H / 2 + 0.05
    s = (frm + [0, dy if up else -dy, 0]) + [0.35 if frm[0] < to[0] else -0.35, 0, 0]
    e = (to + [0, dy if up else -dy, 0]) + [-0.35 if frm[0] < to[0] else 0.35, 0, 0]
    ang = -1.0 if (frm[0] < to[0]) == up else 1.0
    return CurvedArrow(s, e, angle=ang, color=color, stroke_width=3, tip_length=0.2)


def padlock(color, at, s=1.0):
    body = RoundedRectangle(corner_radius=0.06, width=0.46, height=0.36, stroke_color=color, stroke_width=3).set_fill(fillc(color, 0.5), 1)
    shackle = Arc(radius=0.15, start_angle=0, angle=PI, stroke_color=color, stroke_width=4)
    shackle.next_to(body, UP, buff=0)
    legs = VGroup(Line(shackle.get_start(), shackle.get_start() + 0.04 * DOWN), Line(shackle.get_end(), shackle.get_end() + 0.04 * DOWN)).set_stroke(color, 4)
    return VGroup(shackle, legs, body).scale(s).move_to(at)


def person(color):
    head = Circle(radius=0.18, stroke_color=color, stroke_width=3).set_fill(fillc(color, 0.4), 1)
    body = Arc(radius=0.32, start_angle=0, angle=PI, stroke_color=color, stroke_width=3)
    body.next_to(head, DOWN, buff=0.05)
    base = Line(body.get_start(), body.get_end(), stroke_width=3, color=color)
    return VGroup(head, body, base)


def status(k, s, color):
    t = M(s, 19)
    r = RoundedRectangle(corner_radius=0.08, width=max(5.6, t.width + 0.4), height=0.48, stroke_color=color, stroke_width=2.5)
    r.set_fill(fillc(color, 0.18), 1)
    return VGroup(r, t.move_to(r)).move_to([ST_X, ST_Y[k], 0])


class SSI(Base):
    """txn-05, section 3. acct-17 has two cards of 75.00; the total must stay >= 0. Two withdrawals of 100.00 each read
    150.00 and write different cards, so no row lock clashes: -50.00 (write skew). Serializable: version 1 locks reads
    (strict 2PL, MySQL), which deadlocks and brings back waiting. Version 2, SSI: the archive clerk with sign-in slips.
    SIREAD notes, read-write edges B->A and A->B, A commits, B fails with 40001 as a pivot, the retry refuses. The
    pivot shortcut, false alarms and the retry loop. Moral and a check (Repeatable Read)."""

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

    def val(self, k, s, color=WHITE):
        return self.put(f"v{k}", card_val(k, s, color))

    def note(self, k, s, color=GREY_B):
        return self.put(f"n{k}", card_note(k, s, color))

    def total(self, s, color=WHITE):
        return self.put("tot", M(s, 28, color).move_to([LX, TOTAL_Y, 0]))

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("Fifty dollars overdrawn", "and nobody broke a lock")

        # ---------------- scene 1: the question ----------------
        title = fit(T("acct-17: total must not go below 0", 22, GREY_B), 4.6).move_to([LX, 2.95, 0])
        cards = [card(0), card(1)]
        self.steps("Picture one customer's account, acct-17, with two cards. Each card holds 75.00. "
                   "The rule is simple: the account's total must never go below zero.", [
            "with two cards",
            (lambda: [FadeIn(cards[0], shift=0.1 * RIGHT), FadeIn(cards[1], shift=0.1 * RIGHT)], 0.7),
            "Each card holds",
            (lambda: [*self.val(0, "75.00"), *self.val(1, "75.00")], 0.5),
            "The rule",
            (lambda: [FadeIn(title), *self.total("total: 150.00")], 0.6),
        ])
        na = node(GA, "A", "100 from card 1", BLUE_M)
        nb = node(GB, "B", "100 from card 2", PURPLE_M)
        div = DashedLine([DIV_X, 3.0, 0], [DIV_X, -2.55, 0], dash_length=0.1, stroke_width=1.5, color=GREY_D)
        self.steps("Two withdrawals of 100.00 arrive at the same moment, one from each card. Each checks the total first: 150.00. "
                   "Plenty. So each takes 100.", [
            "Two withdrawals",
            (lambda: [Create(div), FadeIn(na, shift=0.1 * DOWN), FadeIn(nb, shift=0.1 * DOWN)], 0.8),
            "Each checks",
            (lambda: [*self.put("sa", status(0, "A reads the total: 150.00", BLUE_M)), *self.put("sb", status(1, "B reads the total: 150.00", PURPLE_M))], 0.6),
            "So each takes",
            (lambda: [*self.val(0, "-25.00", BLUE_M), *self.val(1, "-25.00", PURPLE_M)], 0.6),
        ])
        self.steps("Both commit. Card 1 is at -25.00, card 2 is at -25.00, and the account is 50.00 overdrawn. "
                   "Nobody broke a lock. How did the database let this through?", [
            (lambda: [*self.put("sa", status(0, "A: COMMIT ok", BLUE_M)), *self.put("sb", status(1, "B: COMMIT ok", PURPLE_M))], 0.6),
            "and the account",
            (lambda: [*self.total("total: -50.00", RED_M)], 0.5),
            "How did",
            (lambda: [*self.cap("how did the database let this through?", YELLOW_M, 28)], 0.5),
        ])

        # ---------------- scene 2: different rows, no clash ----------------
        self.steps("Locks put the writers of one row in line. But look at what each withdrawal wrote. The first wrote card 1. "
                   "The second wrote card 2. Different rows, so no lock ever clashed.", [
            (lambda: self.uncap(), 0.4),
            "The first wrote",
            (lambda: [glow(cards[0][0], BLUE_M, 1.03)], 0.7),
            "The second wrote",
            (lambda: [glow(cards[1][0], PURPLE_M, 1.03)], 0.7),
            "no lock ever",
            (lambda: [*self.cap("different rows: no row lock ever clashed", WHITE)], 0.5),
        ])
        self.steps("Run them one after the other, and the second would have seen 50.00, and refused. "
                   "Together, each made its decision from a total the other one was about to change.", [
            (lambda: [*self.val(0, "75.00"), *self.val(1, "75.00"), *self.total("total: 150.00")], 0.5),
            (lambda: [*self.val(0, "-25.00", BLUE_M), *self.total("total: 50.00"), *self.put("sa", status(0, "A first: COMMIT ok", BLUE_M))], 0.6),
            "and refused",
            (lambda: [*self.put("sb", status(1, "then B sees 50.00: refuses", GREEN_M))], 0.6),
            "Together",
            (lambda: [*self.val(1, "-25.00", PURPLE_M), *self.total("total: -50.00", RED_M),
                      *self.put("sa", status(0, "A decided from 150.00", BLUE_M)), *self.put("sb", status(1, "B decided from 150.00", PURPLE_M))], 0.7),
        ])
        self.steps("Each was careful. Just not with each other.", [0.3, (lambda: [glow(na[0], BLUE_M, 1.04), glow(nb[0], PURPLE_M, 1.04)], 0.8)], after=0.4)
        self.steps("This is called write skew: two transactions read the same rows, then write different ones, and a rule breaks. "
                   "Row locks can't see it.", [
            (lambda: [*self.cap("write skew: read the same rows, write different ones", RED_M, 28)], 0.6),
        ])
        self.steps("What we want has a name: serializable. The result must equal running the transactions one at a time, in some order.", [
            "serializable",
            (lambda: [*self.cap("serializable: same result as one at a time, in some order", GREEN_M, 28)], 0.6),
        ])

        # ---------------- scene 3: version 1, reads lock too ----------------
        pl = [padlock(GREY_B, [LX + CARD_W / 2 + 0.45, CARD_Y[k], 0]) for k in (0, 1)]
        self.steps("The first way to get it: make reads lock too. Every row a transaction reads gets a lock, held until it commits.", [
            (lambda: [*self.uncap(), *self.val(0, "75.00"), *self.val(1, "75.00"), *self.total("total: 150.00"),
                      *self.drop("sa", "sb")], 0.6),
            "make reads lock",
            (lambda: [FadeIn(pl[0], scale=0.6), FadeIn(pl[1], scale=0.6), *self.note(0, "read-locked by A and B"), *self.note(1, "read-locked by A and B")], 0.7),
        ])
        self.steps("Now each withdrawal needs to write a card the other one holds. They wait for each other, "
                   "the database stops one, and it runs again.", [
            "They wait",
            (lambda: [*self.put("sa", status(0, "A waits for B's lock on card 1", YELLOW_M)), *self.put("sb", status(1, "B waits for A's lock on card 2", YELLOW_M))], 0.7),
            "the database stops",
            (lambda: [*self.put("sb", status(1, "B stopped: runs again later", RED_M))], 0.6),
        ])
        self.steps("That's correct, and it's how MySQL's serializable works. But it brings the waiting back. "
                   "A month-end report would lock 2 million rows, and every transfer would queue behind it.", [
            "how MySQL's",
            (lambda: [*self.cap("version 1: reads take locks (MySQL's SERIALIZABLE)", WHITE)], 0.5),
            "brings the waiting",
            (lambda: [*self.cap("the cost: readers and writers wait for each other again", RED_M)], 0.5),
        ])
        self.steps("So the wish: readers never wait, and still, somebody notices.", [
            (lambda: [FadeOut(pl[0]), FadeOut(pl[1]), *self.drop("n0", "n1", "sa", "sb"),
                      *self.cap("the wish: readers never wait, and still, somebody notices", GREEN_M, 26)], 0.7),
        ])

        # ---------------- scene 4: the archive clerk ----------------
        clerk = person(GOLD_M).move_to([0.2, 2.6, 0])
        wb_lab = T("the clerk's whiteboard", 20, GOLD_M)
        wb_lab.move_to([0.75 + wb_lab.width / 2, 2.6, 0])
        self.steps("Picture an office archive with a clerk. Anyone can read any folder, with no waiting. "
                   "But on the way out, you sign the folder's slip: I read this.", [
            (lambda: [*self.uncap(), FadeIn(clerk, shift=0.1 * DOWN)], 0.6),
            "Anyone can read",
            (lambda: [*self.cap("the archive: read anything, no waiting", WHITE)], 0.5),
            "you sign",
            (lambda: [*self.note(0, "slip: read by A, B", GOLD_M), *self.note(1, "slip: read by A, B", GOLD_M)], 0.7),
        ])
        e_ba = edge(GB, GA, True, GOLD_M)
        self.steps("When someone changes a folder, the clerk checks its slip. Somebody else read the old one, "
                   "so in any one-at-a-time story, that reader came first. The clerk draws an arrow: reader before writer.", [
            (lambda: [FadeIn(wb_lab)], 0.4),
            "the clerk checks",
            (lambda: [Indicate(self.lab["n0"], color=GOLD_M)], 0.7),
            "The clerk draws",
            (lambda: [Create(e_ba)], 0.7),
        ])
        e_ab0 = edge(GA, GB, False, GOLD_M)
        self.steps("If the arrows ever go round in a circle, no one-at-a-time story fits. The clerk sends someone back to start over.", [
            "go round",
            (lambda: [Create(e_ab0)], 0.7),
            "sends someone back",
            (lambda: [glow(nb[0], RED_M, 1.05)], 0.8),
        ])
        maps = VGroup(*[VGroup(T(a, 21, GOLD_M), T("=", 21, GREY_B), T(b, 21)).arrange(RIGHT, buff=0.2)
                        for a, b in (("a signature on the slip", "an SIREAD lock"), ("an arrow", "a read-write dependency"),
                                     ("sent back", "error 40001, and your retry"))])
        maps.arrange(DOWN, buff=0.18, aligned_edge=LEFT).move_to([3.15, -1.75, 0])
        self.steps("Map it. The signature on the slip is a note PostgreSQL calls an SIREAD lock. The arrow is a read-write dependency. "
                   "Being sent back is an error, and starting over is your program's retry.", [
            "The signature",
            (lambda: [FadeIn(maps[0], shift=0.1 * UP)], 0.5),
            "The arrow is",
            (lambda: [FadeIn(maps[1], shift=0.1 * UP)], 0.5),
            "Being sent back",
            (lambda: [FadeIn(maps[2], shift=0.1 * UP)], 0.5),
        ])

        # ---------------- scene 5: run the cards ----------------
        self.steps("Let's run the cards, under PostgreSQL's serializable. Both withdrawals read both cards. Each read leaves a note. "
                   "The notes block nothing.", [
            (lambda: [FadeOut(VGroup(maps, clerk, wb_lab, e_ba, e_ab0)), *self.drop("n0", "n1"), *self.uncap()], 0.6),
            "Both withdrawals",
            (lambda: [*self.total("both read: 150.00"), *self.put("sa", status(0, "A reads both cards: 150.00", BLUE_M)), *self.put("sb", status(1, "B reads both cards: 150.00", PURPLE_M))], 0.6),
            "leaves a note",
            (lambda: [*self.note(0, "SIREAD: A, B"), *self.note(1, "SIREAD: A, B")], 0.6),
            "block nothing",
            (lambda: [*self.cap("SIREAD lock: a note that says who read this row; it blocks nobody", WHITE)], 0.5),
        ])
        e1 = edge(GB, GA, True, PURPLE_M)
        e1t = T("B read card 1, A wrote it", 18, PURPLE_M).move_to([(GA[0] + GB[0]) / 2, 2.4, 0])
        self.steps("The first withdrawal takes 100 from card 1. The second had read card 1, and won't see this change. "
                   "So the second must come before the first. An arrow, from second to first.", [
            (lambda: [*self.uncap(), *self.val(0, "-25.00", BLUE_M), *self.put("sa", status(0, "A writes card 1", BLUE_M))], 0.6),
            "The second had read",
            (lambda: [Indicate(self.lab["n0"], color=PURPLE_M)], 0.7),
            "An arrow",
            (lambda: [Create(e1), FadeIn(e1t)], 0.7),
        ])
        e2 = edge(GA, GB, False, BLUE_M)
        e2t = T("A read card 2, B wrote it", 18, BLUE_M).move_to([(GA[0] + GB[0]) / 2, -0.75, 0])
        self.steps("Now the second takes 100 from card 2, which the first had read. An arrow, from first to second. "
                   "No row lock clashed, and still, the arrows make a circle.", [
            (lambda: [*self.val(1, "-25.00", PURPLE_M), *self.put("sb", status(1, "B writes card 2", PURPLE_M))], 0.6),
            "An arrow",
            (lambda: [Create(e2), FadeIn(e2t)], 0.7),
            "make a circle",
            (lambda: [*self.cap("A before B, and B before A: no order fits", RED_M), glow(na[0], RED_M, 1.04), glow(nb[0], RED_M, 1.04)], 0.8),
        ])
        self.steps("The first commits. What happens when the second tries to commit? Pause and guess.", [
            (lambda: [*self.uncap(), *self.put("sa", status(0, "A: COMMIT ok", GREEN_M))], 0.6),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("It fails, with error 40001: could not serialize access. The second is a pivot: one arrow in, one arrow out, "
                   "and the transaction at the far end has already committed.", [
            (lambda: [*self.uncap(), *self.put("sb", status(1, "B: COMMIT, ERROR 40001", RED_M))], 0.6),
            "The second is a pivot",
            (lambda: [*self.cap("pivot: one read-write arrow in, one out", WHITE), glow(nb[0], RED_M, 1.05)], 0.7),
            "one arrow in",
            (lambda: [Indicate(e2t, color=BLUE_M)], 0.6),
            "one arrow out",
            (lambda: [Indicate(e1t, color=PURPLE_M)], 0.6),
            "already committed",
            (lambda: [glow(na[0], GREEN_M, 1.04)], 0.6),
        ])
        self.steps("The second withdrawal's change to card 2 is thrown away with it, so nobody will ever see it.", [
            (lambda: [*self.val(1, "75.00"), *self.total("total: 50.00")], 0.7),
        ])
        self.steps("The program's retry runs it again from the start. Its new snapshot sees card 1 at -25.00, the total is 50.00, "
                   "and the withdrawal is refused. The same end as running the first, then the second.", [
            (lambda: [FadeOut(VGroup(e1, e1t, e2, e2t)), *self.drop("n0", "n1")], 0.5),
            "runs it again",
            (lambda: [*self.put("sb", status(1, "B again: reads 50.00, refuses", GREEN_M))], 0.6),
            "The same end",
            (lambda: [*self.cap("the same end as A, then B", GREEN_M, 28), glow(cards[0][0], GREEN_M, 1.02), glow(cards[1][0], GREEN_M, 1.02)], 0.8),
        ])

        # ---------------- scene 6: the name, the shortcut, the cost ----------------
        self.steps("This is serializable snapshot isolation, SSI, PostgreSQL's serializable since version 9.1. "
                   "Readers read their snapshot and never wait. The notes only feed the check.", [
            (lambda: [*self.cap("SSI: serializable snapshot isolation", BLUE_M, 30)], 0.6),
            "never wait",
            (lambda: [*self.cap("readers read their snapshot and never wait", WHITE)], 0.5),
        ])
        e1b, e2b = edge(GB, GA, True, PURPLE_M), edge(GA, GB, False, BLUE_M)
        self.steps("Searching every circle after each write would be slow. The theory behind it shows that every circle has two arrows in a row. "
                   "So PostgreSQL only watches for a transaction with one arrow in and one arrow out.", [
            (lambda: [Create(e1b), Create(e2b)], 0.7),
            "two arrows in a row",
            (lambda: [Indicate(e2b, color=YELLOW_M), Indicate(e1b, color=YELLOW_M)], 0.9),
            "one arrow in",
            (lambda: [*self.cap("the shortcut: watch for a pivot, not for whole circles", WHITE), glow(nb[0], YELLOW_M, 1.05)], 0.8),
        ])
        self.steps("The shortcut has a cost: false alarms. The pattern can appear without a real circle, and notes on a whole table, "
                   "instead of a row, make it more likely.", [
            (lambda: [*self.cap("false alarms: the pattern without a real circle", RED_M)], 0.6),
            "notes on a whole table",
            (lambda: [*self.note(0, "note on the whole table", GREY_B), *self.note(1, "note on the whole table", GREY_B)], 0.6),
        ])
        self.steps("So under serializable, every transaction needs a retry loop: code that runs it again from the start after 40001. "
                   "In exchange, you don't have to study every pair of transactions yourself.", [
            (lambda: [FadeOut(VGroup(e1b, e2b)), *self.drop("n0", "n1"),
                      *self.cap("rule: every SERIALIZABLE transaction gets a retry loop for 40001", YELLOW_M, 26)], 0.7),
            "In exchange",
            (lambda: [glow(na[0], GREEN_M, 1.03), glow(nb[0], GREEN_M, 1.03)], 0.8),
        ])

        # ---------------- scene 7: the moral, and a check ----------------
        self.steps("So how did the account go 50.00 overdrawn? Each withdrawal decided from a total the other was changing, "
                   "and they wrote different rows, so no lock saw it.", [
            (lambda: [*self.val(1, "-25.00", PURPLE_M), *self.total("total: -50.00", RED_M), *self.cap("50.00 overdrawn: how?", WHITE),
                      *self.put("sa", status(0, "A decided from 150.00", BLUE_M)), *self.put("sb", status(1, "B decided from 150.00", PURPLE_M))], 0.7),
            "different rows",
            (lambda: [glow(cards[0][0], BLUE_M, 1.02), glow(cards[1][0], PURPLE_M, 1.02)], 0.8),
        ])
        self.steps("Serializable snapshot isolation keeps notes of who read what, and sends one back. Nobody waits to read.", [
            (lambda: [*self.val(1, "75.00"), *self.total("total: 50.00", GREEN_M), *self.put("sb", status(1, "B: 40001, retried, refused", GREEN_M)),
                      *self.cap("keep notes of who read what, and send one back", YELLOW_M, 28)], 0.8),
        ], after=0.6)
        self.steps("One quick check. Run the same two withdrawals at Repeatable Read instead. "
                   "What are the two cards at the end? Pause and think.", [
            (lambda: [*self.uncap(), *self.val(0, "75.00"), *self.total("total: 150.00"), *self.drop("sa", "sb"),
                      *self.put("lvl", T("REPEATABLE READ", 24, YELLOW_M).move_to([3.15, 2.5, 0]))], 0.7),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("-25.00 each. Both commit, and the account is 50.00 overdrawn. Repeatable Read gives each a snapshot, "
                   "but keeps no notes of who read what.", [
            (lambda: [*self.uncap(), *self.val(0, "-25.00", RED_M), *self.val(1, "-25.00", RED_M), *self.total("total: -50.00", RED_M)], 0.6),
            "Both commit",
            (lambda: [*self.put("sa", status(0, "A: COMMIT ok", BLUE_M)), *self.put("sb", status(1, "B: COMMIT ok", PURPLE_M))], 0.6),
            "keeps no notes",
            (lambda: [*self.cap("a snapshot alone doesn't notice; notes of who read what do", WHITE)], 0.5),
        ], after=0.3)
        self.play(*self.cap("keep notes of who read what, and send one back", YELLOW_M, 28), run_time=0.7)
        self.wait(2.0)
