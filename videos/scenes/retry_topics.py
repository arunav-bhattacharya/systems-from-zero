from sfz import *

SAY.insert(0, (r"\b12x50\b", "twelve x fifty"))
SAY.insert(0, (r"\bpayments\.retry-10s\b", "payments dot retry ten S"))
SAY.insert(0, (r"\bpayments\.retry-1m\b", "payments dot retry one M"))
SAY.insert(0, (r"\bpayments\.DLT\b", "payments dot D L T"))
SAY.insert(0, (r"\bacct-(\d)\b", r"account \1"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
RAIL_Y, SLIP_Y, SLIP_W, SLIP_H = 3.0, 2.4, 1.05, 0.8         # the main rail: partition 0 of payments
MK_Y = 1.83                                                   # the bookmark
CK_C = np.array([-5.5, 2.4, 0])                              # the cook: the ledger
BK_C = np.array([-5.5, 0.15, 0])                             # the card's bank
R2_Y, R3_Y = 0.85, -0.75                                      # the second and third rails (retry topics)
R_X0 = -1.55                                                  # where the side rails start
LAB_X = -4.3                                                  # where the side rails' names start
TR_X0, TR_X1, TR_C_Y, TR_H = -1.55, 2.9, -2.3, 0.72           # the problem tray: payments.DLT
CAP_Y, BAR_Y = -3.42, -3.0


def sx(k):
    return -3.85 + 1.22 * k


def rx(j):
    return R_X0 + 0.65 + 1.25 * j


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

    # labels that get replaced: one key, one thing on screen
    def put(self, key, mob, d=UP):
        old = self.lab.get(key)
        self.lab[key] = mob
        return [swap(old, mob, d)]

    def drop(self, *keys):
        out = []
        for key in keys:
            old = self.lab.pop(key, None)
            if old is not None:
                out.append(FadeOut(old))
        return out

    def cap(self, s, color=GREY_B, size=24):
        return self.put("cap", fit(T(s, size, color), 12.6).move_to([0, CAP_Y, 0]))

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.05):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def slip(k, x, y, color=GREY_B, s=1.0):
    r = RoundedRectangle(corner_radius=0.08, width=SLIP_W, height=SLIP_H, stroke_color=color, stroke_width=2.5)
    r.set_fill(fillc(color, 0.2), 1).move_to([x, y, 0])
    g = VGroup(r, T(f"pay-{k}", 19).move_to([x, y, 0])).set_z_index(3)
    return g.scale(s)


def paint(sl, color):
    return [sl[0].animate.set_stroke(color).set_fill(fillc(color, 0.2), 1)]


def pin(x, y_top):
    return Line([x, RAIL_Y, 0], [x, y_top, 0], stroke_width=2, color=GREY_C)


def side_rail(y):
    return Line([R_X0, y, 0], [6.3, y, 0], stroke_width=3, color=GOLD_M)


def code_panel(title, lines, x):
    r = RoundedRectangle(corner_radius=0.14, width=6.3, height=4.8, stroke_color=GREY_B, stroke_width=2.5).set_fill("#0b0d10", 1)
    r.move_to([x, 0.3, 0])
    head = left_at(T(title, 22, GREY_B), x - 2.9, 2.3)
    rows = VGroup()
    cw = M("x" * 40, 14).width / 40
    for k, s in enumerate(lines):
        col = GREY_B if s.strip().startswith("//") else WHITE
        ind = (len(s) - len(s.lstrip())) * cw
        rows.add(left_at(M(s.strip() if s.strip() else " ", 14, col), x - 2.9 + ind, 1.8 - 0.33 * k))
    if rows.width > 5.6:
        rows.scale(5.6 / rows.width, about_point=rows.get_corner(UL))
    return VGroup(r, head, rows).set_z_index(10)


JAVA = ["// the ledger: send it off to wait, then commit",
        "retry.send(new ProducerRecord<>(",
        "    \"payments.retry-10s\", r.key(), r.value())).get();",
        "consumer.commitSync(nextOffsets(records));",
        "",
        "// the retry reader, at the head of its partition",
        "if (now < r.timestamp() + 10_000) {",
        "    consumer.pause(Set.of(tp));   // keep polling",
        "} else {",
        "    consumer.resume(Set.of(tp));  // due: go back",
        "    consumer.seek(tp, r.offset());",
        "}"]
KOTLIN = ["// the ledger: send it off to wait, then commit",
          "retry.send(ProducerRecord(",
          "    \"payments.retry-10s\", r.key(), r.value())).get()",
          "consumer.commitSync(nextOffsets(records))",
          "",
          "// the retry reader, at the head of its partition",
          "if (now < r.timestamp() + 10_000) {",
          "    consumer.pause(setOf(tp))     // keep polling",
          "} else {",
          "    consumer.resume(setOf(tp))    // due: go back",
          "    consumer.seek(tp, r.offset())",
          "}"]


class RetryTopics(Base):
    """msg-09, section 2. The ledger reads payments in order and keeps a bookmark. The kitchen: slips on a rail, a
    problem tray for a smudged slip (pay-3, 12x50: permanent, the DLT), a short wait when the oven isn't hot
    (transient: 100, 200, 400 ms). The card's bank is down for 3 minutes at 30 payments a second: quick retries put
    5,400 on the tray; 30-second waits hold the rail for 3 of the 5 minutes allowed between polls. Skipping can't work:
    the bookmark is one number. A second rail with a time on each slip: payments.retry-10s. A retry reader in its own
    group pauses (and keeps polling) until the head is due, resumes, seeks back, tries; still failing goes one step
    down, to payments.retry-1m, then the DLT. One wait per topic; the cost: a record that left its partition is
    overtaken. Java and Kotlin, the moral, and a check (a 10-minute record ahead of a 10-second one)."""

    def construct(self):
        self.lab = {}
        self.title_card("Wait somewhere else", "retry topics: how one waiting payment stops holding up the rest")

        # ---------------- scene 1: the question ----------------
        slips = [slip(k, sx(k), SLIP_Y) for k in range(8)]
        ck = RoundedRectangle(corner_radius=0.14, width=1.85, height=1.0, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1).move_to(CK_C)
        self.put("rail_t", left_at(T("payments, in the order they arrived", 22, GREY_B), sx(0) - 0.5, 3.4))
        self.steps("Picture the payments app on an ordinary day. Payments arrive in a line, and a program called the ledger takes them "
                   "one at a time, in order, and keeps each account's balance.", [
            "Payments arrive",
            (lambda: [FadeIn(self.lab["rail_t"]), LaggedStart(*[FadeIn(s, shift=0.15 * LEFT) for s in slips], lag_ratio=0.12)], 1.6),
            "a program called",
            (lambda: [FadeIn(ck), *self.put("ck_t", T("ledger", 22).move_to(CK_C + [0, 0.2, 0])),
                      *self.put("ck_s", T("reads in order", 16, GREY_B).move_to(CK_C + [0, -0.2, 0]))], 0.8),
            "one at a time",
            (lambda: [LaggedStart(*[AnimationGroup(*paint(slips[k], GREEN_M)) for k in range(2)], lag_ratio=0.5)], 1.0),
        ])
        tri = Triangle(color=GOLD_M, fill_opacity=1, stroke_width=0).scale(0.1)
        bm = VGroup(tri)

        def bm_at(k, label="bookmark"):
            t = T(label, 17, GOLD_M)
            t = left_at(t, sx(k) + 0.18, MK_Y - 0.02) if k < 7 else t.move_to([sx(k) - 0.18 - t.width / 2, MK_Y - 0.02, 0])
            return [bm.animate.move_to([sx(k), MK_Y, 0]), *self.put("bm_t", t)]

        tri.move_to([sx(2), MK_Y, 0])
        self.steps("The line is kept by Kafka, a program that stores records in order, for other programs to read. "
                   "The ledger keeps a bookmark: how far it got.", [
            "keeps a bookmark",
            (lambda: [FadeIn(bm, shift=0.1 * UP), *self.put("bm_t", left_at(T("bookmark", 17, GOLD_M), sx(2) + 0.18, MK_Y - 0.02))], 0.7),
        ])
        bk = RoundedRectangle(corner_radius=0.14, width=2.0, height=1.0, stroke_color=BLUE_M, stroke_width=3).set_fill(fillc(BLUE_M), 1).move_to(BK_C)
        call = Arrow(CK_C + [0, -0.55, 0], BK_C + [0, 0.55, 0], buff=0, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.18)
        qm = T("?", 56, YELLOW_M).move_to([-3.0, 0.15, 0])
        self.steps("Now the card's bank, which has to say yes to each payment, stops answering. For three minutes. "
                   "Thirty payments arrive every second. What should the ledger do with the one in front of it? Keep that question.", [
            "Now the card's bank",
            (lambda: [GrowArrow(call), FadeIn(bk), *self.put("bk_t", T("card's bank", 20, BLUE_M).move_to(BK_C + [0, 0.2, 0])),
                      *self.put("bk_s", T("answering", 16, GREEN_M).move_to(BK_C + [0, -0.2, 0]))], 0.8),
            "stops answering",
            (lambda: [bk.animate.set_stroke(RED_M), *self.put("bk_s", T("down for 3 min", 16, RED_M).move_to(BK_C + [0, -0.2, 0]))], 0.6),
            "Thirty payments",
            (lambda: [*self.cap("30 payments a second", WHITE)], 0.5),
            "the one in front",
            (lambda: [glow(slips[2][0], YELLOW_M, 1.1), FadeIn(qm, scale=0.6)], 0.9),
        ])

        # ---------------- scene 2: the kitchen ----------------
        rail = Line([sx(0) - 0.7, RAIL_Y, 0], [6.3, RAIL_Y, 0], stroke_width=4, color=GREY_B)
        pins = VGroup(*[pin(sx(k), SLIP_Y + SLIP_H / 2) for k in range(8)])
        self.steps("Let's step into a kitchen for a minute. Order slips hang on a rail, and the cook takes them in order.", [
            (lambda: [FadeOut(qm), *self.drop("cap")], 0.4),
            "Order slips",
            (lambda: [Create(rail), Create(pins), *self.put("rail_t", left_at(T("the rail of order slips", 22, GREY_B), sx(0) - 0.5, 3.4))], 0.9),
            "the cook",
            (lambda: [*self.put("ck_t", T("the cook", 22).move_to(CK_C + [0, 0.2, 0])), glow(ck, WHITE, 1.05)], 0.8),
        ])
        tray = RoundedRectangle(corner_radius=0.12, width=TR_X1 - TR_X0, height=TR_H, stroke_color=RED_M, stroke_width=3).set_fill(fillc(RED_M), 1)
        tray.move_to([(TR_X0 + TR_X1) / 2, TR_C_Y, 0])
        smudge = M("12x50", 16, RED_M).move_to([sx(3), SLIP_Y - 0.62, 0])
        t3 = slip(3, TR_X0 + 0.55, TR_C_Y, RED_M, 0.75)
        self.steps("A smudged slip that nobody can read goes onto a problem tray, with a note, and the cook moves on. "
                   "That's a permanent failure: trying again won't help. In the app, it's pay-3, whose amount came in as 12x50.", [
            "A smudged slip",
            (lambda: [*paint(slips[3], RED_M), *paint(slips[2], GREEN_M), bm.animate.move_to([sx(3), MK_Y, 0]),
                      *self.put("bm_t", left_at(T("bookmark", 17, GOLD_M), sx(3) + 0.18, MK_Y - 0.02))], 0.6),
            "a problem tray",
            (lambda: [FadeIn(tray), *self.put("tr_t", T("problem tray", 20, RED_M).move_to([TR_X1 - 0.95, TR_C_Y, 0]))], 0.6),
            (lambda: [TransformFromCopy(slips[3], t3), slips[3].animate.set_opacity(0.3)], 0.9),
            "the cook moves on",
            (lambda: bm_at(4), 0.6),
            "permanent failure",
            (lambda: [*self.cap("permanent: the slip itself is wrong", RED_M)], 0.5),
            "In the app",
            (lambda: [FadeIn(smudge, shift=0.1 * UP)], 0.6),
        ])
        tries = VGroup(T("try 1: no answer", 17, RED_M), T("wait 100 ms, try 2: no answer", 17, RED_M),
                       T("wait 200 ms, try 3: yes", 17, GREEN_M)).arrange(DOWN, buff=0.14, aligned_edge=LEFT)
        left_at(tries, -3.9, 0.35)
        self.steps("But if the oven isn't hot yet, the slip is fine. Wait a moment and try again. That's a transient failure. "
                   "The ledger does the same with a slow bank: wait 100 milliseconds, then 200, then 400.", [
            (lambda: [FadeOut(smudge)], 0.3),
            "the slip is fine",
            (lambda: [glow(slips[4][0], BLUE_M, 1.1)], 0.7),
            "transient failure",
            (lambda: [*self.cap("transient: something around the slip was briefly wrong", BLUE_M),
                      bk.animate.set_stroke(GOLD_M), *self.put("bk_s", T("slow", 16, GOLD_M).move_to(BK_C + [0, -0.2, 0]))], 0.6),
            "wait 100",
            (lambda: [FadeIn(tries[0]), FadeIn(tries[1])], 0.6),
            "then 200",
            (lambda: [FadeIn(tries[2])], 0.5),
            (lambda: [*paint(slips[4], GREEN_M), *bm_at(5)], 0.6),
        ])
        self.steps("So the rail is one partition of the payments log, the cook is the ledger, and the tray is a separate log "
                   "for records it gave up on, a dead-letter topic, called payments.DLT.", [
            (lambda: [FadeOut(tries), *self.drop("cap"), bk.animate.set_stroke(BLUE_M),
                      *self.put("bk_s", T("answering", 16, GREEN_M).move_to(BK_C + [0, -0.2, 0]))], 0.5),
            "the rail is",
            (lambda: [*self.put("rail_t", left_at(T("the rail = partition 0 of payments", 22, GREY_B), sx(0) - 0.5, 3.4))], 0.6),
            "the cook is",
            (lambda: [*self.put("ck_t", T("the ledger", 22).move_to(CK_C + [0, 0.2, 0]))], 0.6),
            "the tray is",
            (lambda: [glow(tray, RED_M, 1.03)], 0.6),
            "called payments",
            (lambda: [*self.put("tr_t", M("payments.DLT", 18, RED_M).move_to([TR_X1 - 1.05, TR_C_Y, 0]))], 0.6),
        ])

        # ---------------- scene 3: the outage, predicted ----------------
        cnt = {"v": 0}

        def counter(v, color=RED_M):
            return left_at(T(f"on the tray: {v:,}", 21, color if v else GREY_B), TR_X1 + 0.3, TR_C_Y)

        self.put("tr_n", counter(1))
        t5 = slip(5, TR_X0 + 0.55 + 0.9, TR_C_Y, RED_M, 0.75)
        self.steps("Now back to the bank, down for three minutes. Waits of 100, 200 and 400 milliseconds give up in under a second. "
                   "So pay-5 goes onto the tray. And so does the next one.", [
            (lambda: [bk.animate.set_stroke(RED_M), *self.put("bk_s", T("down for 3 min", 16, RED_M).move_to(BK_C + [0, -0.2, 0])),
                      FadeIn(self.lab["tr_n"])], 0.6),
            "give up",
            (lambda: [*self.cap("100 + 200 + 400 ms: gives up in under a second", RED_M)], 0.5),
            "So pay-5",
            (lambda: [*paint(slips[5], RED_M), TransformFromCopy(slips[5], t5), slips[5].animate.set_opacity(0.3), *self.put("tr_n", counter(2))], 0.9),
            "And so does",
            (lambda: [*paint(slips[6], RED_M), slips[6].animate.set_opacity(0.3), *self.put("tr_n", counter(3)), *bm_at(7)], 0.7),
        ])
        self.steps("Thirty a second, for three minutes. How many good payments end up on the tray? Pause and guess.", [
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        holder = self.lab["tr_n"]

        def upd(m, a):
            v = int(round(3 + (5400 - 3) * a))
            if getattr(m, "_v", None) == v:
                return
            m._v = v
            m.become(counter(v))

        self.steps("Five thousand four hundred. Thirty times a hundred and eighty seconds, every one a good payment, "
                   "waiting for a person to send it back by hand.", [
            (lambda: [*self.cap("30 a second x 180 seconds = 5,400", WHITE), UpdateFromAlphaFunc(holder, upd)], 1.6),
            "waiting for a person",
            (lambda: [glow(tray, RED_M, 1.03)], 0.8),
        ])
        self.steps("That's not a problem tray any more. That's a problem room. So quick retries are for a hiccup, not for an outage.", [
            "a problem room",
            (lambda: [tray.animate(rate_func=there_and_back).stretch(1.12, 0)], 0.8),
            "So quick retries",
            (lambda: self.cap("quick retries: for a hiccup, not an outage", WHITE), 0.5),
        ])

        # ---------------- scene 4: wait longer? (break it) ----------------
        def ck_s(s, color=GOLD_M):
            return self.put("ck_s", T(s, 16, color).move_to(CK_C + [0, -0.2, 0]))

        def reset_main():
            out = [FadeOut(t5), *self.put("tr_n", counter(1))]
            for k in (5, 6):
                out += [slips[k].animate.set_opacity(1), *paint(slips[k], GREY_B)]
            return out

        self.steps("Fine, then wait longer. Thirty seconds between tries, up to six tries. That gives the bank time to come back.", [
            (lambda: [*reset_main(), *bm_at(5), *self.drop("cap")], 0.8),
            "Thirty seconds",
            (lambda: [*ck_s("try 1 of 6"), *paint(slips[5], GOLD_M)], 0.6),
            "up to six",
            (lambda: ck_s("try 4 of 6"), 0.5),
        ])
        gauge_bg = Line([-2.5, BAR_Y, 0], [2.5, BAR_Y, 0], stroke_width=8, color=GREY_D)
        gauge = Line([-2.5, BAR_Y, 0], [-2.5 + 5 * 0.6, BAR_Y, 0], stroke_width=8, color=GOLD_M)
        self.steps("But now the cook stands at the oven with pay-5 for three minutes, and every slip behind it waits. "
                   "And Kafka gives a reader five minutes between two requests for more. After that, it treats the reader as gone.", [
            "every slip behind",
            (lambda: [LaggedStart(*[glow(slips[k][0], GOLD_M, 1.08) for k in (6, 7)], lag_ratio=0.3), *ck_s("try 6 of 6")], 1.0),
            "five minutes",
            (lambda: [Create(gauge_bg), *self.cap("between two requests for more: 3 of the 5 minutes allowed", GOLD_M)], 0.4),
            (lambda: [Create(gauge)], 1.2),
            "treats the reader",
            (lambda: [glow(ck, RED_M, 1.05)], 0.8),
        ])
        self.steps("Short waits flood the tray. Long waits hold up the rail. Well... neither is the kitchen we wanted. "
                   "What we want is for pay-5 to wait somewhere else, while the rail keeps moving.", [
            "Short waits",
            (lambda: [glow(tray, RED_M, 1.03)], 0.6),
            "Long waits",
            (lambda: [glow(slips[5][0], GOLD_M, 1.1)], 0.6),
            "What we want",
            (lambda: [FadeOut(gauge), FadeOut(gauge_bg), *self.cap("the wish: pay-5 waits somewhere else, and the rail keeps moving", WHITE)], 0.6),
        ])

        # ---------------- scene 5: skip it and come back? ----------------
        skip_x = tick(False, 0.14).move_to([sx(5), SLIP_Y + 0.55, 0])
        self.steps("Can't the ledger skip pay-5 and come back to it later? A queue program can hold one message back like that. "
                   "But Kafka's bookmark is a single number. Move it past pay-5, and you've told Kafka that pay-5 is done.", [
            "skip pay-5",
            (lambda: [*self.cap("skip it, and come back later?", PURPLE_M)], 0.5),
            "a single number",
            (lambda: [Indicate(bm, color=GOLD_M, scale_factor=1.6), *bm_at(5, "bookmark: 5")], 0.8),
            "Move it past",
            (lambda: bm_at(6, "bookmark: 6"), 0.6),
            "pay-5 is done",
            (lambda: [Create(skip_x), *self.cap("bookmark at 6 means: everything before 6 is done", RED_M)], 0.6),
        ])

        # ---------------- scene 6: the second rail ----------------
        r2 = side_rail(R2_Y)
        r2_pins = {}
        on2 = {}

        def to_r2(k, j):
            sl = slip(k, rx(j), R2_Y - 0.5, GOLD_M)
            pn = Line([rx(j), R2_Y, 0], [rx(j), R2_Y - 0.1, 0], stroke_width=2, color=GREY_C)
            on2[k], r2_pins[k] = sl, pn
            return [TransformFromCopy(slips[k], sl), FadeIn(pn), slips[k].animate.set_opacity(0.3)]

        self.steps("A good kitchen has a second rail, for slips that wait on something. The cook pins the slip there "
                   "with a time on it, and carries on with the main rail.", [
            (lambda: [FadeOut(skip_x), *bm_at(5), *self.drop("cap")], 0.6),
            "a second rail",
            (lambda: [Create(r2), *self.put("r2_t", fit(T("second rail", 20, GOLD_M), 2.1).move_to([LAB_X + 1.05, R2_Y, 0]))], 0.8),
            "pins the slip",
            (lambda: to_r2(5, 0), 0.9),
            "with a time",
            (lambda: [*self.put("due", T("due in 10 s", 16, GOLD_M).move_to([rx(0), R2_Y - 1.08, 0]))], 0.5),
            "carries on",
            (lambda: [*bm_at(6), *ck_s("carries on", GREEN_M)], 0.6),
        ])
        self.steps("In Kafka, the second rail is another topic, a separate log, called payments.retry-10s. "
                   "The ledger writes pay-5 there, waits for Kafka to confirm it, moves its bookmark past it, and carries on at full speed.", [
            "another topic",
            (lambda: [*self.put("r2_t", fit(M("payments.retry-10s", 17, GOLD_M), 2.1).move_to([LAB_X + 1.05, R2_Y, 0]))], 0.7),
            "waits for Kafka",
            (lambda: [glow(on2[5][0], GOLD_M, 1.1)], 0.6),
            "full speed",
            (lambda: [*to_r2(6, 1), *bm_at(7), *ck_s("full speed", GREEN_M)], 0.7),
        ])
        dues = [T(f"due 0:{10 + j:02d}", 16, GOLD_M).move_to([rx(j), R2_Y - 1.08, 0]) for j in range(2)]
        self.steps("Every record carries the time it was written. So a reader knows pay-5 is due ten seconds after that, "
                   "and the one behind it a little later.", [
            "the time it was written",
            (lambda: [*self.cap("each record keeps the time it was written; due = that time + 10 seconds", WHITE)], 0.5),
            "pay-5 is due",
            (lambda: [*self.put("due", dues[0])], 0.5),
            "the one behind",
            (lambda: [FadeIn(dues[1])], 0.6),
        ])

        # ---------------- scene 7: the retry reader ----------------
        rr = RoundedRectangle(corner_radius=0.12, width=2.1, height=0.9, stroke_color=GOLD_M, stroke_width=3).set_fill(fillc(GOLD_M), 1)
        rr.move_to([LAB_X + 1.05, R2_Y - 0.9, 0])

        def rr_s(s, color=GREY_B):
            return self.put("rr_s", T(s, 15, color).move_to(rr.get_center() + [0, -0.2, 0]))

        self.steps("A second reader, in a group of its own, reads the retry topic. Its first record isn't due yet. Does it sleep? "
                   "No. A long sleep breaks the same five-minute rule.", [
            "A second reader",
            (lambda: [FadeIn(rr), *self.put("rr_t", T("retry reader", 18, GOLD_M).move_to(rr.get_center() + [0, 0.18, 0])),
                      *rr_s("reads the first one"), *self.drop("cap")], 0.8),
            "isn't due yet",
            (lambda: [glow(on2[5][0], GOLD_M, 1.1)], 0.6),
            "Does it sleep",
            (lambda: [*self.cap("sleep until it's due?", PURPLE_M)], 0.5),
            "No.",
            (lambda: [*self.cap("a long sleep: past the five minutes between requests", RED_M)], 0.5),
        ])
        self.steps("Instead, it pauses that partition, and keeps asking Kafka for more. A paused partition hands back nothing, "
                   "but asking keeps the reader in its group.", [
            "it pauses",
            (lambda: [*rr_s("paused, still asking", GOLD_M), r2.animate.set_stroke(opacity=0.35),
                      *self.cap("paused: Kafka hands back nothing from this partition", GOLD_M)], 0.7),
            "keeps asking",
            (lambda: [LaggedStart(*[Indicate(self.lab["rr_s"], color=GOLD_M, scale_factor=1.08) for _ in range(2)], lag_ratio=1.0)], 1.2),
        ])
        r3 = side_rail(R3_Y)
        on3 = slip(5, rx(0), R3_Y - 0.5, GOLD_M)
        pn3 = Line([rx(0), R3_Y, 0], [rx(0), R3_Y - 0.1, 0], stroke_width=2, color=GREY_C)
        self.steps("At ten seconds, it resumes, goes back to pay-5, and calls the bank again. Still down? "
                   "Then pay-5 moves one step down, to a topic with a longer wait, payments.retry-1m.", [
            "it resumes",
            (lambda: [r2.animate.set_stroke(opacity=1), *rr_s("resumed: pay-5", GREEN_M), *self.drop("cap")], 0.6),
            "calls the bank",
            (lambda: [glow(bk, RED_M, 1.05), *paint(on2[5], RED_M)], 0.8),
            "one step down",
            (lambda: [Create(r3), *self.put("r3_t", fit(M("payments.retry-1m", 17, GOLD_M), 2.1).move_to([LAB_X + 1.05, R3_Y, 0]))], 0.7),
            (lambda: [TransformFromCopy(on2[5], on3), FadeIn(pn3), on2[5].animate.set_opacity(0.3), *self.drop("due")], 0.9),
        ])
        SX = R_X0 - 0.3
        stair = VGroup(Arrow([SX, R2_Y - 0.12, 0], [SX, R3_Y + 0.12, 0], buff=0, stroke_width=3, color=GOLD_M,
                             max_tip_length_to_length_ratio=0.12),
                       Arrow([SX, R3_Y - 0.12, 0], [TR_X0 - 0.12, TR_C_Y + 0.2, 0], buff=0, stroke_width=3, color=RED_M,
                             max_tip_length_to_length_ratio=0.15))
        self.steps("The last step is the tray. Steps with growing waits, one under the other, like a staircase. "
                   "These are called retry topics.", [
            "The last step",
            (lambda: [GrowArrow(stair[0]), GrowArrow(stair[1])], 0.9),
            "like a staircase",
            (lambda: [*self.cap("10 seconds, then 1 minute, then the tray", WHITE)], 0.5),
            "retry topics",
            (lambda: [*self.cap("retry topics: a staircase of topics with growing waits", GOLD_M),
                      glow(r2, GOLD_M, 1.0), glow(r3, GOLD_M, 1.0)], 0.9),
        ])
        self.steps("When the bank comes back, the main rail carries on at once. The records on the steps go through on their next try. "
                   "Only what still fails at the last step reaches the tray.", [
            "When the bank",
            (lambda: [bk.animate.set_stroke(BLUE_M), *self.put("bk_s", T("answering", 16, GREEN_M).move_to(BK_C + [0, -0.2, 0])), *self.drop("cap")], 0.6),
            "the main rail",
            (lambda: [*paint(slips[7], GREEN_M), *bm_at(8)], 0.7),
            "go through",
            (lambda: [LaggedStart(*[AnimationGroup(*paint(s, GREEN_M)) for s in (on2[6], on3)], lag_ratio=0.5)], 1.0),
            "Only what still",
            (lambda: [glow(tray, RED_M, 1.03), *self.cap("the tray: only what fails at every step", RED_M)], 0.8),
        ])

        # ---------------- scene 8: the guardrails ----------------
        self.steps("One rule keeps the retry reader simple: each topic has one wait. Every record on the ten-second rail waits "
                   "the same ten seconds, so they come due in the order they were written. The reader only ever watches the first one.", [
            (lambda: [*self.drop("cap")], 0.3),
            "each topic has one wait",
            (lambda: [*self.cap("one wait per topic", WHITE)], 0.5),
            "come due in the order",
            (lambda: [Indicate(dues[1], color=GOLD_M, scale_factor=1.2)], 0.8),
            "only ever watches",
            (lambda: [glow(on2[6][0], GOLD_M, 1.1)], 0.7),
        ])

        def tag(sl):
            t = T("acct-1", 14, PURPLE_M).move_to(sl[0].get_center() + [0, -0.2, 0]).set_z_index(5)
            return t, [sl[1].animate.shift(0.15 * UP), FadeIn(t)]

        tg7, a7 = tag(slips[7])
        tg5, a5 = tag(on3)
        self.steps("And one cost. Notice what just happened. pay-7 went through first, while pay-5 was still waiting on a step. "
                   "Say they belong to the same account. Its payments are now out of order.", [
            "Notice what",
            (lambda: [glow(slips[7][0], GREEN_M, 1.1)], 0.6),
            "while pay-5",
            (lambda: [glow(on3[0], GOLD_M, 1.1)], 0.6),
            "Say they belong",
            (lambda: [*a7, *a5], 0.7),
            "out of order",
            (lambda: [*self.cap("one account: pay-7 applied before pay-5", PURPLE_M)], 0.6),
        ])
        self.steps("For a receipt email, that does no harm. For a payment and its refund, it does. "
                   "Keeping an account in order is the next part of the lesson.", [
            "For a receipt",
            (lambda: [*self.cap("a receipt email: fine.   a payment and its refund: a problem", WHITE)], 0.5),
            "Keeping an account",
            (lambda: [glow(slips[7][0], PURPLE_M, 1.1), glow(on3[0], PURPLE_M, 1.1)], 0.8),
        ])
        # ---------------- scene 9: the code ----------------
        diagram = VGroup(*[m for m in self.mobjects if isinstance(m, VMobject)])
        diagram.save_state()
        jp = code_panel("Java", JAVA, -3.3)
        kp = code_panel("Kotlin", KOTLIN, 3.3)

        def hl(panel, rows, color):
            return [panel[2][r].animate(rate_func=there_and_back).set_color(color) for r in rows]

        self.steps("Here's the heart of it, in Java and in Kotlin.", [
            (lambda: [diagram.animate.set_opacity(0.06)], 0.7),
            (lambda: [FadeIn(jp, shift=0.1 * UP), FadeIn(kp, shift=0.1 * UP)], 0.8),
        ])
        self.steps("The ledger sends the payment to the retry topic, waits for the answer, and only then commits its bookmark.", [
            "sends the payment",
            (lambda: [*hl(jp, (1, 2), GOLD_M), *hl(kp, (1, 2), GOLD_M)], 1.4),
            "only then commits",
            (lambda: [*hl(jp, (3,), GREEN_M), *hl(kp, (3,), GREEN_M)], 1.2),
        ])
        self.steps("The retry reader adds ten seconds to the record's time. Not due yet: pause, and keep polling. Due: resume, "
                   "and seek back to the record.", [
            "adds ten seconds",
            (lambda: [*hl(jp, (6,), GOLD_M), *hl(kp, (6,), GOLD_M)], 1.0),
            "Not due yet",
            (lambda: [*hl(jp, (7,), GOLD_M), *hl(kp, (7,), GOLD_M)], 1.0),
            "Due: resume",
            (lambda: [*hl(jp, (9, 10), GREEN_M), *hl(kp, (9, 10), GREEN_M)], 1.4),
        ], after=0.6)

        # ---------------- scene 10: the moral, and a check ----------------
        self.steps("So, what should the ledger do with the payment in front of it while the bank is down? "
                   "Not stand at the oven, and not throw it on the tray. Pin it to a second rail with a time, and keep the main rail moving.", [
            (lambda: [FadeOut(jp), FadeOut(kp), Restore(diagram)], 0.8),
            (lambda: [*self.cap("what should the ledger do with the payment in front of it?", WHITE)], 0.4),
            "Not stand",
            (lambda: [glow(ck, GOLD_M, 1.05)], 0.6),
            "not throw it",
            (lambda: [glow(tray, RED_M, 1.03)], 0.6),
            "Pin it",
            (lambda: [glow(r2, GOLD_M, 1.0), *self.cap("pin it to a second rail with a time", GOLD_M, 30)], 0.8),
        ])
        self.steps("Quick retries for a hiccup. Retry topics for an outage. The tray for what's really broken.", [
            (lambda: [glow(ck, BLUE_M, 1.05)], 0.6),
            "Retry topics",
            (lambda: [glow(r2, GOLD_M, 1.0), glow(r3, GOLD_M, 1.0)], 0.7),
            "The tray",
            (lambda: [glow(tray, RED_M, 1.03)], 0.6),
        ], after=0.5)

        def side_slip(k, j, color, label):
            sl = slip(k, rx(j), R2_Y - 0.5, color)
            return VGroup(sl, Line([rx(j), R2_Y, 0], [rx(j), R2_Y - 0.1, 0], stroke_width=2, color=GREY_C),
                          T(label, 16, color).move_to([rx(j), R2_Y - 1.08, 0]))

        long_s = side_slip(9, 0, RED_M, "waits 10 min")
        short_s = side_slip(10, 1, GOLD_M, "waits 10 s")
        self.steps("One quick check. Someone puts a ten-minute record and a ten-second record on the same retry topic, "
                   "the ten-minute one first. When does the ten-second one get its try? Pause and think.", [
            (lambda: [FadeOut(VGroup(*on2.values(), *r2_pins.values(), dues[1])), *self.drop("cap")], 0.6),
            "a ten-minute record",
            (lambda: [FadeIn(long_s, shift=0.1 * DOWN)], 0.6),
            "a ten-second record",
            (lambda: [FadeIn(short_s, shift=0.1 * DOWN)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("After ten minutes. The reader only watches the first record, so the short wait is stuck behind the long one. "
                   "That's why each wait gets its own topic.", [
            (lambda: [*self.cap("after ten minutes: stuck behind the first record", RED_M), glow(long_s[0][0], RED_M, 1.1)], 0.8),
            "stuck behind",
            (lambda: [glow(short_s[0][0], GOLD_M, 1.1)], 0.7),
            "its own topic",
            (lambda: [*self.cap("one wait per topic", GOLD_M, 32)], 0.6),
        ], after=0.4)
        self.wait(2.0)
