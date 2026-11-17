from sfz import *

SAY.insert(0, (r"\bClientHello\b", "client hello"))
SAY.insert(0, (r"\bServerHello\b", "server hello"))
SAY.insert(0, (r"\bHelloRetryRequest\b", "hello retry request"))
SAY.insert(0, (r"\bCertificateVerify\b", "certificate verify"))
SAY.insert(0, (r"\bapi\.pay\.test\b", "A P I dot pay dot test"))
SAY.insert(0, (r"\bx25519\b", "X twenty-five five nineteen"))
SAY.insert(0, (r"\bTLS 1\.3\b", "T L S one point three"))
SAY.insert(0, (r"\bTLS 1\.2\b", "T L S one point two"))
SAY.insert(0, (r"\bhellos\b", "hello messages"))   # Kokoro says "halos"

# ---- the one picture: a ladder (frame about 14.2 x 8; everything stays 0.5 inside) ----
LX, BX, KX = -5.15, -2.3, 5.0          # lifelines: your laptop, the Wi-Fi box, the bank
AY, SY = 3.0, 2.2                     # the actors' row, and the state line under each actor
LIFE_TOP, LIFE_BOT = 1.9, -2.35
ROW_Y = [1.45, 0.6, -0.25, -1.1, -1.95]  # one row per crossing; each crossing takes 35 ms
LAB_X = (BX + KX) / 2                  # row labels sit between the box and the bank
PANEL_Y, BAR_Y, CAP_Y = -2.75, -3.06, -3.36


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


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def swap(old, new, d=UP):
    """Replace one label with another: the old one leaves before the new one arrives, so they never overlap."""
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def dot_run(a, b, color=YELLOW_M, rt=0.8):
    d = Dot(radius=0.08, color=color).move_to(a)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=rt),
                      FadeOut(d, run_time=0.15))


# ---- the pieces ----
def actor(name, sub, x, color, w=2.5, mono=False):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=1.1, stroke_color=color, stroke_width=3)
    r.set_fill(fillc(color), 1).move_to([x, AY, 0])
    return VGroup(r, T(name, 28).move_to([x, AY + 0.21, 0]), (M if mono else T)(sub, 19, GREY_B).move_to([x, AY - 0.26, 0]))


def lifeline(x):
    return DashedLine([x, LIFE_TOP, 0], [x, LIFE_BOT, 0], dash_length=0.1, stroke_width=2, color=GREY_D)


def row(k, right=True, color=GREY_B, opacity=1.0, double=False):
    y = ROW_Y[k]
    a, b = ([LX + 0.05, y, 0], [KX - 0.05, y, 0]) if right else ([KX - 0.05, y, 0], [LX + 0.05, y, 0])
    cls = DoubleArrow if double else Arrow
    ar = cls(a, b, buff=0, stroke_width=3, color=color, max_tip_length_to_length_ratio=0.025)
    return ar.set_opacity(opacity)


def run(k, right=True, color=YELLOW_M, rt=0.8):
    y = ROW_Y[k]
    a, b = [LX + 0.1, y, 0], [KX - 0.1, y, 0]
    return dot_run(a, b, color, rt) if right else dot_run(b, a, color, rt)


def lab(k, *parts):
    """A row label: parts (mobjects) side by side, centred between the box and the bank, just above the arrow."""
    return VGroup(*parts).arrange(RIGHT, buff=0.15).move_to([LAB_X, ROW_Y[k] + 0.32, 0])


def tlab(k, ms, right, color=GREY_B):
    t = T(f"{ms} ms", 22, color)
    return left_at(t, KX + 0.22, ROW_Y[k]) if right else right_at(t, LX - 0.22, ROW_Y[k])


def eye(k):
    e = Ellipse(width=0.44, height=0.26, stroke_color=YELLOW_M, stroke_width=3).set_fill(BLACK, 1)
    return VGroup(e, Dot(radius=0.065, color=YELLOW_M)).move_to([BX, ROW_Y[k], 0])


def padlock(c=ORIGIN, s=1.0, color=GOLD_M):
    body = RoundedRectangle(corner_radius=0.04, width=0.3, height=0.23, stroke_color=color, stroke_width=3).set_fill(BLACK, 1)
    sh = Arc(radius=0.095, start_angle=0, angle=PI, stroke_color=color, stroke_width=3)
    sh.next_to(body, UP, buff=0)
    g = VGroup(sh, body).scale(s)
    return g.move_to(c)


def lock_mark(k):
    return padlock([BX, ROW_Y[k] + 0.04, 0], 1.0)


class TlsHandshake(Base):
    """net-10, section 2. Your laptop on café Wi-Fi, the Wi-Fi box that reads everything, and a bank 70 ms away (there
    and back) on one ladder diagram, time going down. The careful way (ask, then send your half) costs two round trips
    after TCP's; ordering in two languages abroad is the guess; the ClientHello and ServerHello are open and carry key
    shares; the box could play both parts; the locked certificate, CertificateVerify and Finished prove who answered;
    175 ms before the bank sees the payment; HelloRetryRequest, pools, what stays visible; a check question."""

    def cap(self, s, color=GREY_B, size=24):
        new = T(s, size, color).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def state(self, who, s, color=GREY_B):
        x = {"L": LX, "B": BX, "K": KX}[who]
        new = T(s, 20, color).move_to([x, SY, 0]) if s else None
        old, self.st[who] = self.st[who], new
        if new is None:
            return [FadeOut(old)] if old is not None else []
        return [swap(old, new)]

    def panel(self, s):
        new = left_at(T(s, 22, YELLOW_M), -2.05, PANEL_Y)
        old, self.pb = self.pb, new
        out = [swap(old, new)]
        if self.ph is None:
            self.ph = right_at(T("the Wi-Fi box saw:", 22, GREY_B), -2.27, PANEL_Y)
            out.append(FadeIn(self.ph))
        return out

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def construct(self):
        self.capm = self.pb = self.ph = None
        self.st = {"L": None, "B": None, "K": None}
        self.title_card("Two hellos, then a lock", "how TLS 1.3 sets up a secret line in one round trip")

        lap = actor("your laptop", "in the café", LX, BLUE_M)
        box = actor("Wi-Fi box", "behind the counter", BX, GREY_B, w=2.5)
        bank = actor("the bank", "api.pay.test", KX, GREEN_M, mono=True)
        lines = VGroup(lifeline(LX), lifeline(BX), lifeline(KX))

        # ---------------- scene 1: the padlock ----------------
        self.steps("You're in a café, on its free Wi-Fi, paying a bill on your bank's website.", [
            (lambda: [FadeIn(lap, shift=0.15 * RIGHT)], 0.6),
            "paying a bill",
            (lambda: [FadeIn(bank, shift=0.15 * LEFT)], 0.6),
        ])
        e0 = eye(1)
        self.steps("Every packet you send goes first through the little Wi-Fi box behind the counter, and it can read anything that passes.", [
            "through the little",
            (lambda: [FadeIn(box, shift=0.15 * DOWN), Create(lines)], 0.8),
            "and it can read",
            (lambda: [run(1)], 0.9),
            (lambda: [FadeIn(e0, scale=0.5), *self.state("B", "reads all it can", YELLOW_M)], 0.4),
        ])
        big = padlock([LAB_X, -0.1, 0], 3.2)
        self.steps("And yet, in less than a fifth of a second, a padlock appears.", [
            "a padlock",
            (lambda: [FadeIn(big, scale=0.6)], 0.6),
        ])
        qm = T("?", 60, YELLOW_M).move_to([LAB_X + 1.6, 0.2, 0])
        self.steps("So how do your laptop and the bank agree on a secret key while the box reads every word, and that fast?", [
            "agree on a secret",
            (lambda: [glow(lap[0], BLUE_M), glow(bank[0], GREEN_M)], 0.8),
            "while the box",
            (lambda: [glow(box[0], YELLOW_M)], 0.8),
            "and that fast",
            (lambda: [FadeIn(qm, scale=0.6)], 0.5),
        ])
        self.steps("It's tempting to think the padlock hides everything, from the very first word. Hold that thought.", [
            "the padlock hides",
            (lambda: self.cap("the padlock hides everything, from the first word?", WHITE), 0.5),
            "Hold that",
            (lambda: [FadeOut(big), FadeOut(qm), FadeOut(e0), *self.uncap(), *self.state("B", None)], 0.6),
        ])

        # ---------------- scene 2: every question costs a wait ----------------
        self.steps("Let's put the bank 70 milliseconds away, there and back. That's one round trip, and every wait for an answer costs one.", [
            "70 milliseconds",
            (lambda: [run(0, True, WHITE, 0.7)], 0.7),
            (lambda: [run(0, False, WHITE, 0.7)], 0.7),
            "That's one round trip",
            (lambda: self.cap("one round trip: 70 ms there and back, 35 ms each way"), 0.5),
        ])
        r0 = row(0, double=True)
        r0l = lab(0, T("TCP's handshake: one round trip", 22, GREY_B))
        t0 = tlab(0, 70, False)
        self.steps("First, the two programs open a TCP connection, the protocol underneath that delivers bytes in order. "
                   "That's one round trip already.", [
            (lambda: self.uncap(), 0.3),
            "open a TCP",
            (lambda: [GrowFromCenter(r0), FadeIn(r0l, shift=0.1 * UP)], 0.8),
            "one round trip already",
            (lambda: [FadeIn(t0, shift=0.1 * LEFT)], 0.5),
        ])
        ghost_spec = [(1, True, "which kinds of key exchange do you accept?", 105), (2, False, "these kinds", 140),
                      (3, True, "my half", 175), (4, False, "my half", 210)]
        ghosts = [(row(k, r, GREY_B, 0.55), lab(k, T(s, 22, GREY_A)), tlab(k, ms, r, GREY_A)) for k, r, s, ms in ghost_spec]

        def ghost(i):
            a, l, t = ghosts[i]
            return [GrowArrow(a), FadeIn(l, shift=0.1 * UP), FadeIn(t)]

        self.steps("Now, the careful way to set up a lock. Ask which kinds of key exchange the bank accepts, and wait. "
                   "Then send your half, and wait for the bank's.", [
            "Ask which",
            (lambda: ghost(0), 0.7),
            "and wait",
            (lambda: ghost(1), 0.7),
            "Then send",
            (lambda: ghost(2), 0.7),
            "wait for the bank's",
            (lambda: ghost(3), 0.7),
        ])
        self.steps("Two more round trips before your payment can leave. TLS 1.2, the version before, needed two as well.", [
            (lambda: [*self.cap("two more round trips: the payment leaves at 210 ms"),
                      Indicate(ghosts[3][2], color=RED_M, scale_factor=1.25)], 0.9),
        ])
        self.steps("Wouldn't it be nice to skip the asking?", [
            (lambda: [*self.cap("wouldn't it be nice to skip the asking?", WHITE),
                      *[FadeOut(VGroup(*g)) for g in ghosts]], 0.9),
        ], after=0.5)

        # ---------------- scene 3: ordering abroad ----------------
        lap_txt, bank_txt = VGroup(lap[1], lap[2]), VGroup(bank[1], bank[2])
        you = VGroup(T("a traveller", 28).move_to(lap[1]), T("that's you", 19, GREY_B).move_to(lap[2]))
        cashier = VGroup(T("the cashier", 28).move_to(bank[1]), T("in a café abroad", 19, GREY_B).move_to(bank[2]))
        self.steps("Picture a café abroad. You're not sure if the cashier speaks English or French.", [
            (lambda: [*self.uncap(), box.animate.set_opacity(0.15), lines[1].animate.set_opacity(0.15),
                      VGroup(r0, r0l, t0).animate.set_opacity(0.15)], 0.8),
            (lambda: [swap(lap_txt, you), swap(bank_txt, cashier)], 0.8),
            "English or French",
            (lambda: self.cap("English or French?"), 0.5),
        ])
        ask1 = (row(1, True, GREY_B, 0.55), lab(1, T("English or French?", 22, GREY_A)))
        ask2 = (row(2, False, GREY_B, 0.55), lab(2, T("French.", 22, GREY_A)))
        r1 = row(1, True, WHITE)
        r2 = row(2, False, WHITE)
        o1 = lab(1, T("a coffee, please  /  un café, s'il vous plaît", 22))
        o2 = lab(2, T("in French: coming right up", 22))
        self.steps("You could ask, and wait. Instead, you say your order twice, in English and in French. "
                   "The cashier answers in French. One whole wait, saved.", [
            (lambda: [*self.uncap(), GrowArrow(ask1[0]), FadeIn(ask1[1])], 0.6),
            (lambda: [GrowArrow(ask2[0]), FadeIn(ask2[1])], 0.6),
            "Instead",
            (lambda: [FadeOut(VGroup(*ask1, *ask2))], 0.5),
            "you say your order",
            (lambda: [GrowArrow(r1), FadeIn(o1, shift=0.1 * UP)], 0.7),
            (lambda: [run(1, True, WHITE)], 0.8),
            "The cashier answers",
            (lambda: [GrowArrow(r2), FadeIn(o2, shift=0.1 * UP)], 0.7),
            (lambda: [run(2, False, WHITE)], 0.8),
            "One whole wait",
            (lambda: self.cap("one whole wait, saved"), 0.5),
        ])
        langs = VGroup(T("English", 22, YELLOW_M), T("French", 22, YELLOW_M)).arrange(RIGHT, buff=1.2).move_to([LAB_X, ROW_Y[3] + 0.1, 0])
        self.steps("Let's map it. Each language is a kind of key exchange, which TLS calls a group.", [
            "Each language",
            (lambda: [*self.cap("a language = a kind of key exchange"), FadeIn(langs, shift=0.1 * UP)], 0.6),
            "which TLS calls",
            (lambda: [*self.cap("TLS calls each kind a group"),
                      Transform(langs, VGroup(T("group 1", 22, YELLOW_M), T("group 2", 22, YELLOW_M)).arrange(RIGHT, buff=1.2).move_to(langs))], 0.7),
        ])
        ch = lab(1, T("ClientHello:", 22), M("api.pay.test", 20), T("· two key shares", 22))
        sh = lab(2, T("ServerHello: picks one group, and its key share", 22))
        self.steps("Your order in each language is a key share, your half of the exchange, made in advance for each group you guess. "
                   "The cashier's answer is the bank's reply.", [
            "is a key share",
            (lambda: [*self.cap("your order in each language = a key share, made in advance"),
                      Transform(langs, VGroup(T("key share 1", 22, YELLOW_M), T("key share 2", 22, YELLOW_M)).arrange(RIGHT, buff=1.2).move_to(langs))], 0.7),
            "The cashier's answer",
            (lambda: [FadeOut(langs), swap(o1, ch), swap(o2, sh), swap(you, lap_txt), swap(cashier, bank_txt),
                      box.animate.set_opacity(1), lines[1].animate.set_opacity(1), VGroup(r0, r0l, t0).animate.set_opacity(1),
                      *self.uncap()], 1.0),
        ])

        # ---------------- scene 4: two open hellos ----------------
        e1, e2 = eye(1), eye(2)
        self.steps("So your laptop's first message, the ClientHello, carries the guesses. It names the server, api.pay.test, "
                   "lists the methods it accepts, and carries two key shares.", [
            "It names",
            (lambda: [Indicate(ch[1], color=YELLOW_M, scale_factor=1.15)], 0.7),
            "two key shares",
            (lambda: [run(1)], 0.9),
            (lambda: [FadeIn(e1, scale=0.5), *self.panel("api.pay.test, two key shares")], 0.5),
        ])
        self.steps("The bank answers with the ServerHello. It picks one group, and sends its own key share.", [
            "It picks",
            (lambda: [run(2, False)], 0.9),
            (lambda: [FadeIn(e2, scale=0.5), *self.panel("api.pay.test, both sides' key shares")], 0.5),
        ])
        self.steps("Here the café picture stops: saying it twice makes nothing secret. The secret comes from this lesson's first section. "
                   "Each side keeps a secret at home, and sends only a public value.", [
            (lambda: self.cap("where the café picture stops: saying it twice makes nothing secret"), 0.6),
            "Each side keeps",
            (lambda: [*self.uncap(), *self.state("L", "a secret, kept at home", GOLD_M), *self.state("K", "a secret, kept at home", GOLD_M)], 0.7),
            "a public value",
            (lambda: [Indicate(e1, color=YELLOW_M), Indicate(e2, color=YELLOW_M)], 0.8),
        ])
        self.steps("Each mixes its own secret with the other's public value, and both get the same key. "
                   "The box saw both public values, and can't.", [
            "both get the same key",
            (lambda: [*self.state("L", "the same key", GREEN_M), *self.state("K", "the same key", GREEN_M)], 0.7),
            "and can't",
            (lambda: self.state("B", "can't work it out", RED_M), 0.6),
        ])
        self.steps("And notice, the box read both hellos. The padlock doesn't hide the first words: "
                   "the box knows you're talking to api.pay.test.", [
            "the box read",
            (lambda: [glow(e1[0], YELLOW_M, 1.2), glow(e2[0], YELLOW_M, 1.2)], 0.8),
            "The padlock doesn't",
            (lambda: self.cap("the two hellos are open: the padlock starts after them"), 0.6),
            "the box knows",
            (lambda: [Indicate(self.pb, color=YELLOW_M, scale_factor=1.06)], 0.8),
        ])

        # ---------------- scene 5: a lock with nobody behind it ----------------
        ka = T("key A, with you", 22, RED_M).move_to([(LX + BX) / 2, ROW_Y[3] + 0.05, 0])
        kb = T("key B, with the bank", 22, RED_M).move_to([LAB_X, ROW_Y[3] + 0.05, 0])
        self.steps("So we have a key the box can't work out. Are we done? Against a box that only listens, yes.", [
            (lambda: self.cap("a key the box can't work out: are we done?", WHITE), 0.6),
            "Against a box",
            (lambda: self.cap("against a box that only listens: yes"), 0.5),
        ])
        self.steps("But the box can also talk. It can play the bank to your laptop, and your laptop to the bank. "
                   "Two keys, and it reads everything in between.", [
            "the box can also talk",
            (lambda: [*self.uncap(), box[0].animate.set_stroke(RED_M), *self.state("B", "plays both parts", RED_M)], 0.6),
            "It can play the bank",
            (lambda: [FadeIn(ka, shift=0.1 * RIGHT), *self.state("L", "key A", RED_M)], 0.6),
            "your laptop to the bank",
            (lambda: [FadeIn(kb, shift=0.1 * LEFT), *self.state("K", "key B", RED_M)], 0.6),
            "it reads everything",
            (lambda: [glow(box[0], RED_M, 1.05)], 0.8),
        ])
        self.steps("Both locks work perfectly. They lock you in with the wrong person. "
                   "A lock on its own proves nothing about who holds the other key.", [
            "A lock on its own",
            (lambda: self.cap("a lock on its own proves nothing about who holds the other key", WHITE), 0.6),
        ], after=0.5)

        # ---------------- scene 6: the locked flight ----------------
        r3 = row(3, False, GOLD_M)
        m3 = lock_mark(3)
        t3 = T("certificate, CertificateVerify, Finished", 22, GOLD_M)
        l3 = lab(3, padlock(s=0.8), t3)
        p3 = [l3[0], VGroup(*t3[:11]), VGroup(*t3[11:28]), VGroup(*t3[28:])]   # the padlock, then each message's name
        self.steps("That's what the rest of the bank's reply is for. Everything after the ServerHello is locked.", [
            (lambda: [*self.uncap(), FadeOut(ka), FadeOut(kb), box[0].animate.set_stroke(GREY_B),
                      *self.state("B", "can't work it out", RED_M), *self.state("L", "the same key", GREEN_M),
                      *self.state("K", "the same key", GREEN_M)], 0.7),
            "Everything after",
            (lambda: [GrowArrow(r3), FadeIn(p3[0])], 0.7),
            (lambda: [run(3, False, GOLD_M)], 0.9),
            (lambda: [FadeIn(m3, scale=0.5), *self.panel("api.pay.test, both key shares, then only sizes and timing")], 0.5),
        ])
        self.steps("First, the certificate, the bank's passport from the last section: "
                   "this public key belongs to api.pay.test, signed by a certificate authority.", [
            (lambda: [FadeIn(p3[1], shift=0.1 * UP)], 0.5),
            "this public key",
            (lambda: self.cap("the certificate: this public key belongs to api.pay.test"), 0.5),
            "signed by",
            (lambda: self.cap("signed by a certificate authority"), 0.5),
        ])
        self.steps("But anyone can copy a passport. So the bank also signs every byte of the conversation so far, "
                   "with a private key that never leaves the bank. That's CertificateVerify.", [
            "So the bank also signs",
            (lambda: [*self.cap("a signature over every byte so far"), FadeIn(p3[2], shift=0.1 * UP)], 0.6),
            "with a private key",
            (lambda: [*self.cap("made with the private key, which never leaves the bank"), glow(bank[0], GREEN_M)], 0.8),
            "That's Certificate",
            (lambda: [Indicate(p3[2], color=GOLD_M, scale_factor=1.12)], 0.7),
        ])
        self.steps("Last, Finished: a short code worked out from every byte so far. "
                   "If the box had changed one word of the hellos, the codes wouldn't match.", [
            (lambda: [*self.cap("Finished: a short code over every byte so far"), FadeIn(p3[3], shift=0.1 * UP)], 0.6),
            "If the box had changed",
            (lambda: [Indicate(ch, color=RED_M, scale_factor=1.05), Indicate(sh, color=RED_M, scale_factor=1.05)], 0.9),
        ])
        fake = Arrow([BX - 0.05, ROW_Y[4], 0], [LX + 0.05, ROW_Y[4], 0], buff=0, stroke_width=3, color=RED_M,
                     max_tip_length_to_length_ratio=0.08)
        fx = tick(False, 0.15).move_to([(LX + BX) / 2, ROW_Y[4] + 0.32, 0])
        self.steps("The box has a copy of the passport, but not the private key. "
                   "It can't make the signature, so your laptop's check fails, and it hangs up.", [
            (lambda: [*self.cap("the box: a copied certificate, no private key", RED_M), GrowArrow(fake)], 0.7),
            "It can't make",
            (lambda: [Create(fx)], 0.4),
            "and it hangs up",
            (lambda: self.state("L", "check fails: hangs up", RED_M), 0.6),
            0.8,
            (lambda: [FadeOut(fake), FadeOut(fx), *self.state("L", "the same key", GREEN_M), *self.uncap()], 0.5),
        ])
        r4 = row(4, True, GOLD_M)
        m4 = lock_mark(4)
        l4 = lab(4, padlock(s=0.8), T("Finished, and your payment", 22, GOLD_M))
        self.steps("With the real bank, every check passes. Your laptop sends its own Finished, "
                   "with your payment in the same flight, and new keys lock your data.", [
            (lambda: [*self.cap("the chain, the name, the signature: all pass", GREEN_M), glow(lap[0], GREEN_M)], 0.8),
            "Your laptop sends",
            (lambda: [GrowArrow(r4), FadeIn(l4, shift=0.1 * UP)], 0.7),
            (lambda: [run(4, True, GOLD_M)], 0.9),
            (lambda: [FadeIn(m4, scale=0.5)], 0.3),
            "new keys",
            (lambda: [*self.state("L", "new keys, for data", GREEN_M), *self.state("K", "new keys, for data", GREEN_M)], 0.6),
        ])

        # ---------------- scene 7: count the wait ----------------
        self.steps("So how long before the bank sees the first byte of your payment? Pause and guess.", [
            (lambda: self.cap("how long before the bank sees your payment?", WHITE), 0.6),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        t2 = tlab(2, 140, False)
        t3 = tlab(3, 140, False)
        t4 = tlab(4, 175, True, WHITE)
        self.steps("TCP, 70 milliseconds. The two hellos, one round trip, 70 more. Then the payment's one-way trip, 35. "
                   "That's 175 milliseconds. The careful way would take 245.", [
            (lambda: [*self.uncap(), Indicate(t0, color=WHITE, scale_factor=1.3)], 0.6),
            "The two hellos",
            (lambda: [FadeIn(t2, shift=0.1 * LEFT), FadeIn(t3, shift=0.1 * LEFT)], 0.6),
            "Then the payment",
            (lambda: [FadeIn(t4, shift=0.1 * RIGHT)], 0.5),
            "That's 175",
            (lambda: [*self.cap("70 + 70 + 35 = 175 ms", WHITE), Indicate(t4, color=GREEN_M, scale_factor=1.3)], 0.8),
            "The careful way",
            (lambda: self.cap("175 ms, where asking first would take 245 ms", WHITE), 0.5),
        ])

        # ---------------- scene 8: name it, and the guardrails ----------------
        self.steps("This opening exchange is the TLS handshake: the messages two programs swap before any real data. "
                   "TLS 1.3 needs one round trip, because your laptop guesses.", [
            "the TLS handshake",
            (lambda: [*self.cap("the TLS handshake: the opening messages, before any real data", WHITE),
                      LaggedStart(*[Indicate(m, color=YELLOW_M, scale_factor=1.04) for m in (ch, sh, l3)], lag_ratio=0.3)], 1.2),
            "TLS 1.3 needs",
            (lambda: self.cap("TLS 1.3: one round trip, thanks to the guess", WHITE), 0.5),
        ])
        self.steps("Three guardrails. A wrong guess costs one more round trip: the bank answers with a HelloRetryRequest, "
                   "and your laptop says hello again. That's why clients always send a share for x25519, which nearly every server accepts.", [
            "A wrong guess",
            (lambda: [*self.cap("1. a wrong guess: one more round trip", RED_M), Indicate(ch, color=RED_M, scale_factor=1.05)], 0.8),
            "HelloRetryRequest",
            (lambda: self.cap("the bank sends a HelloRetryRequest; your laptop says hello again", RED_M), 0.5),
            "That's why",
            (lambda: self.cap("so clients always send a share for x25519", GREY_B), 0.5),
        ])
        self.steps("Every new connection pays both round trips. So programs keep a connection pool, "
                   "a set of open connections they reuse, and pay once.", [
            (lambda: [*self.cap("2. every new connection: two round trips", WHITE),
                      LaggedStart(*[Indicate(m, color=WHITE, scale_factor=1.05) for m in (r0l, ch, sh)], lag_ratio=0.3)], 1.0),
            "So programs keep",
            (lambda: self.cap("a connection pool: open connections, reused, so you pay once", WHITE), 0.5),
        ])
        self.steps("And the hellos are open. The box still sees the name, the addresses, and how much you send.", [
            (lambda: [*self.cap("3. the hellos are open: the box sees the name, the addresses, the sizes", YELLOW_M),
                      glow(e1[0], YELLOW_M, 1.2), glow(e2[0], YELLOW_M, 1.2)], 0.8),
            "and how much",
            (lambda: [Indicate(self.pb, color=YELLOW_M, scale_factor=1.06)], 0.8),
        ])

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So: two open hellos carry the guesses. Everything after is locked, "
                   "and a signature only the real bank can make proves who answered.", [
            (lambda: [*self.cap("two open hellos carry the guesses", WHITE), glow(e1[0], YELLOW_M, 1.2), glow(e2[0], YELLOW_M, 1.2)], 0.8),
            "Everything after",
            (lambda: [*self.cap("everything after is locked", GOLD_M), glow(m3[1], GOLD_M, 1.2), glow(m4[1], GOLD_M, 1.2)], 0.8),
            "and a signature",
            (lambda: [*self.cap("a signature only the real bank can make proves who answered", WHITE),
                      Indicate(p3[2], color=GOLD_M, scale_factor=1.12)], 0.8),
        ])
        self.steps("Guess, so you don't have to ask. Sign, so the lock means something.", [
            (lambda: self.cap("guess, so you don't have to ask; sign, so the lock means something", YELLOW_M), 0.6),
        ], after=0.6)
        self.steps("One quick check. The bank accepts neither group your laptop guessed. "
                   "How long before it sees your payment now? Pause and think.", [
            (lambda: self.uncap(), 0.3),
            "The bank accepts neither",
            (lambda: [*self.cap("the bank accepts neither group", RED_M), Indicate(ch, color=RED_M, scale_factor=1.05)], 0.8),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        t4b = left_at(T("245 ms", 22, RED_M), KX + 0.22, ROW_Y[4])
        self.steps("245 milliseconds: one extra round trip for the HelloRetryRequest. "
                   "A wrong guess costs exactly what asking first would have.", [
            (lambda: [*self.uncap(), swap(t4, t4b)], 0.6),
            "one extra",
            (lambda: self.cap("175 + one round trip (70) = 245 ms"), 0.5),
            "A wrong guess costs",
            (lambda: self.cap("a wrong guess costs what asking first would have", WHITE), 0.5),
        ], after=0.4)
        self.wait(2.0)
