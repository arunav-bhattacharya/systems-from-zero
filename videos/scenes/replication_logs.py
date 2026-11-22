from sfz import *

SAY.insert(0, (r"\bMySQL\b", "my S Q L"))
SAY.insert(0, (r"\bm1\b", "M one"))
SAY.insert(0, (r"\bm2's\b", "M two's"))
SAY.insert(0, (r"\bm2\b", "M two"))
SAY.insert(0, (r"\b5\.1\b", "five point one"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
LG_X0, LG_X1, LG_TOP, LG_BOT = -6.55, 6.55, 3.4, 0.95       # the log panel
LINE5 = [2.7, 2.32, 1.94, 1.56, 1.18]
LINE6 = [2.74, 2.42, 2.1, 1.78, 1.46, 1.14]
TB = {"L": (-6.55, -0.35), "F": (0.35, 6.55)}               # the two tables
TB_TOP, TB_BOT = 0.6, -2.0
T_TITLE, T_HEAD, T_ROW, T_VERDICT = 0.3, -0.15, [-0.6, -1.05], -1.6
COLS = [0.35, 0.95, 1.85, 2.65, 4.45]                       # id, shop, fee, ref, created_at (from the left edge)
CAP_Y, BAR_Y = -3.25, -2.75
TCOL = {"L": BLUE_M, "F": TEAL_M}

STMTS = ["INSERT INTO payments (...) VALUES ('m1', 1250, 0, md5(random()::text), now());",
         "INSERT INTO payments (...) VALUES ('m2', 4000, 0, md5(random()::text), now());",
         "INSERT INTO payments (...) VALUES ('m1', 990, 0, md5(random()::text), now());",
         "UPDATE payments SET fee = fee + 30 WHERE merchant = 'm1';",
         "DELETE FROM payments WHERE merchant = 'm2' LIMIT 1;"]
PINNED = {0: "INSERT INTO payments (...) VALUES ('m1', 1250, 0, '23c52a1a', 1000010);",
          2: "INSERT INTO payments (...) VALUES ('m1', 990, 0, 'e0934861', 1000030);"}
ROWLOG = ["insert id=1 merchant=m1 amount=1250 fee=0 ref=23c52a1a created_at=1000010",
          "insert id=2 merchant=m2 amount=4000 fee=0 ref=a4b105b0 created_at=1000020",
          "insert id=3 merchant=m1 amount=990 fee=0 ref=e0934861 created_at=1000030",
          "update id=1 -> merchant=m1 amount=1250 fee=30 ref=23c52a1a created_at=1000010",
          "update id=3 -> merchant=m1 amount=990 fee=30 ref=e0934861 created_at=1000030",
          "delete id=2"]
LEADER = {0: ["1", "m1", "0", "23c52a1a", "1000010"], 1: ["3", "m1", "0", "e0934861", "1000030"]}
STMTCOPY = {0: ["1", "m1", "0", "d850e0b3", "1000360"], 1: ["3", "m1", "0", "e936623d", "1000380"]}


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

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.02):
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def panel(x0, x1, top, bot, color):
    return RoundedRectangle(corner_radius=0.14, width=x1 - x0, height=top - bot, stroke_color=color, stroke_width=3).set_fill(
        fillc(color), 1).move_to([(x0 + x1) / 2, (top + bot) / 2, 0])


def log_line(i, s, color=WHITE, n=5, size=16):
    ys = LINE5 if n == 5 else LINE6
    num = T(str(i + 1), 16, GREY_B).move_to([LG_X0 + 0.32, ys[i], 0]) if n == 5 else VGroup()
    txt = fit(M(s, size, color), LG_X1 - LG_X0 - 0.9)
    return VGroup(num, left_at(txt, LG_X0 + 0.6, ys[i]))


def tcell(side, r, c, s, color=WHITE):
    x0 = TB[side][0]
    return left_at(M(s, 18, color), x0 + COLS[c], T_ROW[r])


class ReplicationLogs(Base):
    """repl-02, section 0. The café's text message (raise prices 10 cents, date at the top), read the next morning and
    delivered twice. A statement log: the lesson's five statements, run by follower S 350 ms later with its tail resent:
    other codes, times 350 ms later, fee 60. Pinning the leader's values fixes codes and times, not the fee. Same result
    every time (durable execution's rule). The row log: statement 4 became two entries; follower R matches. Rule and the
    DELETE ... LIMIT check."""

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def put(self, key, mob, d=UP):
        old, self.m[key] = self.m.get(key), mob
        return [swap(old, mob, d)]

    def drop(self, *keys):
        out = []
        for k in keys:
            old = self.m.pop(k, None)
            if old is not None:
                out.append(FadeOut(old))
        return out

    def drop_prefix(self, p):
        return self.drop(*[k for k in list(self.m) if k.startswith(p)])

    def row(self, side, r, vals, colors=None):
        anims = []
        for c, v in enumerate(vals):
            col = colors[c] if colors else WHITE
            anims += self.put(f"{side}{r}{c}", tcell(side, r, c, v, col), RIGHT)
        return anims

    def cellset(self, side, r, c, v, color=WHITE):
        return self.put(f"{side}{r}{c}", tcell(side, r, c, v, color), RIGHT)

    def title(self, side, s):
        x0, x1 = TB[side]
        return self.put(f"title{side}", T(s, 22, TCOL[side]).move_to([(x0 + x1) / 2, T_TITLE, 0]))

    def ltitle(self, s):
        return self.put("ltitle", left_at(T(s, 20, GREY_B), LG_X0 + 0.3, LG_TOP - 0.28))

    def countdown_cap(self):
        return self.cap("pause and guess", YELLOW_M)

    def construct(self):
        self.capm = None
        self.m = {}
        self.title_card("Send the instruction, or the result?", "what one entry of a replication log should say")

        # ---------------- scene 1: the café's text ----------------
        lp = panel(LG_X0, LG_X1, LG_TOP, LG_BOT, GREY_B)
        tl = panel(*TB["L"], TB_TOP, TB_BOT, BLUE_M)
        tf = panel(*TB["F"], TB_TOP, TB_BOT, TEAL_M)

        def price(side, k, s, color=WHITE):
            x0, x1 = TB[side]
            y = [-0.25, -0.7, -1.25][k]
            return self.put(f"p{side}{k}", T(s, 24, color).move_to([(x0 + x1) / 2, y, 0]))

        self.steps("Picture a café with two branches that keep the same price list.", [
            (lambda: [FadeIn(tl), FadeIn(tf), *self.title("L", "branch 1: price list"), *self.title("F", "branch 2: price list")], 0.8),
            (lambda: [*price("L", 0, "coffee 2.50"), *price("L", 1, "tea 2.00"), *price("L", 2, "dated: today", GREY_B),
                      *price("F", 0, "coffee 2.50"), *price("F", 1, "tea 2.00"), *price("F", 2, "dated: today", GREY_B)], 0.8),
        ])
        msg = T("\"Raise every price by 10 cents, and write today's date at the top.\"", 24, YELLOW_M).move_to([0, 2.0, 0])
        self.steps("The owner changes prices at the first branch, and texts the manager of the second: "
                   "raise every price by 10 cents, and write today's date at the top.", [
            "The owner changes",
            (lambda: [*price("L", 0, "coffee 2.60"), *price("L", 1, "tea 2.10")], 0.6),
            "and texts",
            (lambda: [FadeIn(lp), *self.ltitle("a text message"), *self.put("msg", msg)], 0.8),
        ])
        self.steps("He reads the text the next morning, so his list carries a different date.", [
            (lambda: [*price("F", 0, "coffee 2.60"), *price("F", 1, "tea 2.10")], 0.6),
            "a different date",
            (lambda: price("F", 2, "dated: the next day", RED_M), 0.6),
        ])
        msg2 = T("not delivered... sending again", 20, GREY_B).move_to([0, 1.35, 0])
        self.steps("Then her phone says: not delivered, and sends the text again. And the second branch raises its prices twice.", [
            (lambda: self.put("msg2", msg2), 0.6),
            "raises its prices",
            (lambda: [*price("F", 0, "coffee 2.70", RED_M), *price("F", 1, "tea 2.20", RED_M)], 0.6),
        ])
        self.steps("Sending the instruction felt natural. It's short, and anyone can read it. "
                   "But the second branch did the work again, at another time, and got another answer.", [
            "short",
            (lambda: [Indicate(msg, color=YELLOW_M, scale_factor=1.04)], 0.8),
            "did the work again",
            (lambda: self.cap("the second branch worked it out again: another time, another answer", RED_M), 0.6),
        ])
        self.steps("Coffee at branch two is now the priciest in town.", [
            (lambda: [Indicate(self.m["pF0"], color=RED_M, scale_factor=1.15)], 0.8),
        ], after=0.5)

        # ---------------- scene 2: a statement in the log ----------------
        self.steps("Databases face the same choice. In One leader, many followers, the leader wrote every change into a numbered log, "
                   "and the followers applied it in order. But what does one entry actually say?", [
            (lambda: [*self.uncap(), *self.drop_prefix("p"), *self.drop("msg", "msg2"), *self.title("L", "leader"),
                      *self.title("F", "follower"), *self.ltitle("the leader's log")], 0.8),
            "numbered log",
            (lambda: [*[self.put(f"n{i}", T(str(i + 1), 16, GREY_B).move_to([LG_X0 + 0.32, LINE5[i], 0]))[0] for i in range(5)]], 0.6),
            "what does one entry",
            (lambda: self.put("q", T("?", 40, YELLOW_M).move_to([0, LINE5[0], 0])), 0.5),
        ])
        batch = log_line(0, "UPDATE payments SET status = 'paid_out' WHERE batch_id = 42;", WHITE)
        self.steps("Changes arrive as statements. A statement is one command in SQL, the language most databases take commands in. "
                   "This one marks every payment in batch 42 as paid out to its shop.", [
            (lambda: [*self.drop("q", *[f"n{i}" for i in range(5)]), *self.cap("a statement: one command in SQL, the language of databases", WHITE)], 0.6),
            "This one",
            (lambda: [*self.put("l0", batch), *self.ltitle("statement log")], 0.7),
        ])
        self.steps("The simplest log writes the statement down. 59 bytes, even if it changes 80,000 rows. A person can read it.", [
            "59 bytes",
            (lambda: self.cap("59 bytes in the log, even for 80,000 rows", WHITE), 0.6),
            "A person can",
            (lambda: [Indicate(batch, color=WHITE, scale_factor=1.03)], 0.8),
        ])
        self.steps("MySQL, a popular free database, copied changes only this way until version 5.1. "
                   "It's the text message: each follower runs it again.", [
            (lambda: self.cap("MySQL, a popular free database: only statements until 5.1", WHITE), 0.6),
            "each follower runs",
            (lambda: [*self.cap("the text message: each follower runs it again", YELLOW_M), glow(tf, TEAL_M)], 0.8),
        ])

        # ---------------- scene 3: the demo, and a guess ----------------
        heads = {s: VGroup(*[left_at(T(h, 17, GREY_B), TB[s][0] + COLS[c], T_HEAD, ) for c, h in
                             enumerate(["id", "shop", "fee", "ref", "created_at"])]) for s in TB}
        self.steps("Let's test it with the lesson's demo. The leader runs five statements.", [
            (lambda: [*self.uncap(), *self.drop("l0"), FadeIn(heads["L"]), FadeIn(heads["F"]), *self.title("F", "follower S")], 0.6),
            "five statements",
            (lambda: [LaggedStart(*[FadeIn(m) for m in [self.put(f"l{i}", log_line(i, STMTS[i]))[0].mobject for i in range(5)]], lag_ratio=0.25)], 1.4),
        ])
        self.steps("Three add a payment, each with a reference code made from a random number, and the time from now.", [
            (lambda: [Indicate(self.m["l0"], color=YELLOW_M, scale_factor=1.02)], 0.6),
            (lambda: self.row("L", 0, LEADER[0]), 0.6),
            "a reference code",
            (lambda: [Indicate(self.m["L03"], color=YELLOW_M)], 0.6),
            "the time from now",
            (lambda: [Indicate(self.m["L04"], color=YELLOW_M), *self.row("L", 1, LEADER[1])], 0.7),
        ])
        self.steps("One adds a fee of 30 to every payment of shop m1. And one deletes shop m2's payment.", [
            (lambda: [Indicate(self.m["l3"], color=YELLOW_M, scale_factor=1.02)], 0.5),
            (lambda: [*self.cellset("L", 0, 2, "30"), *self.cellset("L", 1, 2, "30")], 0.6),
            "And one deletes",
            (lambda: [Indicate(self.m["l4"], color=YELLOW_M, scale_factor=1.02)], 0.6),
        ])
        self.steps("Follower S runs each statement 350 milliseconds after the leader. Then, as can happen after a reconnect, "
                   "the end of the log arrives a second time.", [
            (lambda: self.cap("follower S: each statement, 350 ms later", WHITE), 0.6),
            "the end of the log",
            (lambda: [*self.cap("...and the end of the log arrives twice", WHITE),
                      self.m["l3"].animate(rate_func=there_and_back).shift(0.15 * RIGHT),
                      self.m["l4"].animate(rate_func=there_and_back).shift(0.15 * RIGHT)], 0.8),
        ])
        self.steps("Will the follower's table match the leader's? Pause and guess.", [
            (lambda: [glow(tl, BLUE_M), glow(tf, TEAL_M), *self.countdown_cap()], 0.8),
        ], after=0)
        self.countdown(3.0)

        # ---------------- scene 4: not one row matches ----------------
        R = RED_M
        self.steps("Not one row matches. Look at payment 1. The reference code: the follower drew its own random number.", [
            (lambda: [*self.uncap(), *self.row("F", 0, STMTCOPY[0]), *self.row("F", 1, STMTCOPY[1])], 0.8),
            "Look at payment 1",
            (lambda: [Indicate(self.m["F00"], color=YELLOW_M, scale_factor=1.3)], 0.5),
            "The reference code",
            (lambda: [*self.cellset("F", 0, 3, "d850e0b3", R), *self.cellset("F", 1, 3, "e936623d", R)], 0.6),
        ])
        self.steps("The time: 350 milliseconds later, from the follower's own clock.", [
            (lambda: [*self.cellset("F", 0, 4, "1000360", R), *self.cellset("F", 1, 4, "1000380", R),
                      *self.cap("1000010 on the leader, 1000360 on the follower: 350 ms later", WHITE)], 0.7),
        ])
        self.steps("And the fee: 60, not 30, because \"add 30\" arrived twice, and ran twice.", [
            (lambda: [*self.cellset("F", 0, 2, "30"), *self.cellset("F", 1, 2, "30")], 0.5),
            "arrived twice",
            (lambda: [self.m["l3"].animate(rate_func=there_and_back).shift(0.15 * RIGHT)], 0.5),
            (lambda: [*self.cellset("F", 0, 2, "60", R), *self.cellset("F", 1, 2, "60", R)], 0.6),
            (lambda: self.put("vF", T("statement copy equals the leader: false", 18, R).move_to([sum(TB["F"]) / 2, T_VERDICT, 0])), 0.5),
        ])
        self.steps("It's the café again. The date at the top is now. The double price rise is the fee.", [
            (lambda: self.cap("the date at the top: now().   the double price rise: fee + 30, twice.", YELLOW_M), 0.7),
        ])
        ids = VGroup(T("leader: client A gets id 7, client B gets id 8, B becomes final first", 20, WHITE),
                     T("follower: runs B first, and gives it id 7", 20, R)).arrange(DOWN, buff=0.12).move_to([0, -2.55, 0])
        self.steps("And there are quieter ways to differ. Two clients add a payment at the same moment. The leader gives them ids 7 and 8, "
                   "but the second becomes final first, so the follower runs it first, and gives it 7.", [
            (lambda: self.uncap(), 0.3),
            "The leader gives",
            (lambda: [FadeIn(ids[0])], 0.6),
            "so the follower",
            (lambda: [FadeIn(ids[1])], 0.6),
        ])
        self.steps("Each follower did exactly what the log said. The log just told it to think for itself.", [
            (lambda: [FadeOut(ids)], 0.5),
            "think for itself",
            (lambda: self.cap("the log told the follower to think for itself", WHITE), 0.6),
        ], after=0.5)

        # ---------------- scene 5: write the leader's values in ----------------
        self.steps("Can the leader repair this? It can write its own values into each statement: the actual code and the actual time, "
                   "instead of random and now.", [
            (lambda: self.uncap(), 0.3),
            "write its own values",
            (lambda: [*self.put("l0", log_line(0, PINNED[0], GREEN_M)), *self.put("l2", log_line(2, PINNED[2], GREEN_M))], 0.8),
        ])
        self.steps("MySQL does some of this. Which difference goes away, and which one stays? Pause and guess.", [
            (lambda: self.cap("MySQL writes in the leader's time, and warns about random", WHITE), 0.6),
            "Pause and guess",
            (lambda: self.countdown_cap(), 0.4),
        ], after=0)
        self.countdown(3.0)
        G = GREEN_M
        self.steps("Codes and times now match. The fee is still 60. Writing in the leader's values doesn't make \"add 30\" safe to repeat.", [
            (lambda: [*self.uncap(), *self.cellset("F", 0, 3, "23c52a1a", G), *self.cellset("F", 1, 3, "e0934861", G),
                      *self.cellset("F", 0, 4, "1000010", G), *self.cellset("F", 1, 4, "1000030", G)], 0.8),
            "The fee is still",
            (lambda: [Indicate(self.m["F02"], color=R, scale_factor=1.4), Indicate(self.m["F12"], color=R, scale_factor=1.4)], 0.8),
            "doesn't make",
            (lambda: self.cap("\"add 30\", run twice, adds 60", R), 0.6),
        ])

        # ---------------- scene 6: the rule underneath ----------------
        self.steps("The rule underneath: a statement must give the same result every time it runs, wherever it runs.", [
            (lambda: self.cap("a statement must give the same result every time, wherever it runs", YELLOW_M), 0.7),
        ])
        self.steps("Durable execution met the same rule: a workflow reads the time and random numbers through the engine, "
                   "so every replay makes the same choices. For SQL, nothing enforces it.", [
            (lambda: self.cap("durable execution: time and random numbers come through the engine", WHITE), 0.6),
            "For SQL",
            (lambda: self.cap("for SQL: nothing enforces it", RED_M), 0.6),
        ])

        # ---------------- scene 7: log what it did ----------------
        self.steps("So log what the statement did instead. The row log says: payment 1, fee 30, with the leader's own code and time.", [
            (lambda: [*self.uncap(), *self.drop(*[f"l{i}" for i in range(5)]), *self.ltitle("row log"), *self.drop("vF"),
                      *self.drop_prefix("F0"), *self.drop_prefix("F1"), *self.title("F", "follower R")], 0.6),
            (lambda: [LaggedStart(*[FadeIn(m) for m in [self.put(f"r{i}", log_line(i, ROWLOG[i], WHITE, n=6, size=15))[0].mobject
                                                       for i in range(6)]], lag_ratio=0.2)], 1.4),
            "payment 1, fee 30",
            (lambda: [Indicate(self.m["r3"], color=YELLOW_M, scale_factor=1.02)], 0.7),
        ])
        self.steps("Statement 4 became two row entries, one for each row it changed.", [
            (lambda: [Indicate(self.m["r3"], color=YELLOW_M, scale_factor=1.02), Indicate(self.m["r4"], color=YELLOW_M, scale_factor=1.02)], 1.0),
        ])
        self.steps("And the row copy matches the leader exactly, resend and all.", [
            (lambda: [*self.row("F", 0, ["1", "m1", "30", "23c52a1a", "1000010"], [G] * 5),
                      *self.row("F", 1, ["3", "m1", "30", "e0934861", "1000030"], [G] * 5)], 0.8),
            "resend and all",
            (lambda: [self.m["r3"].animate(rate_func=there_and_back).shift(0.15 * RIGHT),
                      *self.put("vF", T("row copy equals the leader: true", 18, G).move_to([sum(TB["F"]) / 2, T_VERDICT, 0]))], 0.7),
        ])

        # ---------------- scene 8: rule and check ----------------
        self.steps("So the rule to keep: a statement runs again on every follower. Unless something forces the same result, "
                   "don't ship statements. Ship what they did.", [
            (lambda: self.cap("a statement runs again on every follower", WHITE), 0.6),
            "Unless something",
            (lambda: self.cap("unless something forces the same result, don't ship statements. Ship what they did.", YELLOW_M), 0.7),
        ], after=0.6)
        # the check: shop m2's payments, stored in a different order on each side
        order_l, order_f = ["a", "b", "c", "d", "e", "f"], ["d", "a", "f", "b", "e", "c"]

        def stack(side, order):
            x0, x1 = TB[side]
            g = VGroup(*[VGroup(RoundedRectangle(corner_radius=0.05, width=0.62, height=0.5, stroke_color=GREY_B, stroke_width=2).set_fill(BLACK, 1),
                                M(o, 20)) for o in order])
            for b in g:
                b[1].move_to(b[0])
            g.arrange(RIGHT, buff=0.12).move_to([(x0 + x1) / 2, -0.8, 0])
            return g

        sl, sf = stack("L", order_l), stack("F", order_f)
        self.steps("One quick check. A follower that was loaded from a copy receives: delete shop m2's payments, limit 100. "
                   "Does it delete the same 100 as the leader? Pause and think.", [
            (lambda: [*self.uncap(), *self.drop(*[f"r{i}" for i in range(6)], "vF"), *self.drop_prefix("L0"), *self.drop_prefix("L1"),
                      *self.drop_prefix("F0"), *self.drop_prefix("F1"), FadeOut(heads["L"]), FadeOut(heads["F"]),
                      *self.title("F", "follower, loaded from a copy"), *self.ltitle("statement log")], 0.7),
            "delete shop",
            (lambda: [*self.put("l0", log_line(0, "DELETE FROM payments WHERE merchant = 'm2' LIMIT 100;")),
                      FadeIn(sl), FadeIn(sf),
                      *self.put("hint", T("shop m2's payments, in the order each one stores them (pictured: 6 of them, LIMIT 3)", 18, GREY_B).move_to([0, -2.4, 0]))], 0.8),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("No. It deletes the first 100 it meets, and it stores its rows in another order. So it deletes other rows.", [
            (lambda: [*self.uncap(), *[sl[i][0].animate.set_stroke(R).set_fill(R, 0.35) for i in range(3)]], 0.6),
            "the first 100",
            (lambda: [*[sf[i][0].animate.set_stroke(R).set_fill(R, 0.35) for i in range(3)]], 0.6),
            "So it deletes",
            (lambda: [*self.cap("leader deletes a, b, c.   follower deletes d, a, f.", R)], 0.6),
        ], after=0.4)
        self.play(*self.cap("unless something forces the same result, don't ship statements. Ship what they did.", YELLOW_M), run_time=0.7)
        self.wait(2.0)
