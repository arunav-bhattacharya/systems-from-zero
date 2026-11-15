from sfz import *

SAY.insert(0, (r"\bClientHello\b", "client hello"))
SAY.insert(0, (r"\bServerHello\b", "server hello"))
SAY.insert(0, (r"\bapi\.pay\.test\b", "A P I dot pay dot test"))

CX, RX, IX, AY, LANE = -4.85, 0.0, 4.85, 2.75, 1.6   # client, router, issuer; the actors' row and the message lane
CL, IL = -6.5, 3.25                                   # left edges of the client and issuer columns
ROW = [0.75, 0.05, -0.65, -1.35, -2.05, -2.75, -3.3]


def fillc(color):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), 0.14)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(path, color=YELLOW_M, run_time=1.0, back=False):
    """A dot that runs along a line (or back along it) and stays invisible until its turn."""
    a, b = (path.get_end(), path.get_start()) if back else (path.get_start(), path.get_end())
    d = Dot(radius=0.08, color=color).move_to(a).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


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


def actor(name, color, x, sub=None, w=3.3):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=1.1, stroke_color=color, stroke_width=3)
    r.set_fill(fillc(color), 1).move_to([x, AY, 0])
    if sub:
        return VGroup(r, T(name, 28).move_to([x, AY + 0.2, 0]), M(sub, 18, GREY_B).move_to([x, AY - 0.25, 0]))
    return VGroup(r, T(name, 28).move_to([x, AY, 0]))


def at(m, x):
    """Lane position for a message at x, kept inside the frame."""
    half = m.width / 2
    return [min(max(x, -6.55 + half), 6.55 - half), LANE, 0]


def msg(text, color, x, size=24, mono=False):
    c = chip(text, color, size, mono)
    return c.move_to(at(c, x))


def _txt(s, color, size, mono):
    return (M if mono else T)(s, size, color)


def cl(s, k, color=WHITE, size=26, mono=False):
    t = _txt(s, color, size, mono)
    return t.move_to([CL + t.width / 2, ROW[k], 0])


def il(s, k, color=WHITE, size=26, mono=False):
    t = _txt(s, color, size, mono)
    return t.move_to([IL + t.width / 2, ROW[k], 0])


def rl(s, k, color=WHITE, size=24, mono=False):
    return _txt(s, color, size, mono).move_to([RX, ROW[k], 0])


def cert(name, signer, x, y, color=GREEN_M, w=3.3, key=None):
    h = 1.25 if key else 0.85
    r = RoundedRectangle(corner_radius=0.1, width=w, height=h, stroke_color=color, stroke_width=2.5)
    r.set_fill(fillc(color), 1).move_to([x, y, 0])
    if key:
        return VGroup(r, M(name, 20).move_to([x, y + 0.36, 0]), M(key, 17, GREY_B).move_to([x, y, 0]),
                      T("signed by " + signer, 19, GREY_B).move_to([x, y - 0.36, 0]))
    return VGroup(r, M(name, 20).move_to([x, y + 0.17, 0]), T("signed by " + signer, 19, GREY_B).move_to([x, y - 0.2, 0]))


class TlsHandshake(Base):
    """net-10, section 2: a checkout service and a card issuer with a router in between. The router reads and rewrites a
    plain request; a toy key exchange (5 and 23; secrets 6 and 15; shares 8 and 19; key 2) rides in the ClientHello and
    ServerHello; a man in the middle runs two exchanges; the certificate chain to a trusted root and the CertificateVerify
    signature stop it; records carry a tag; and what the router still sees."""

    def construct(self):
        self.title_card("The TLS 1.3 handshake", "one round trip to a shared key, and a certificate that proves who answered")

        client = actor("checkout service", BLUE_M, CX)
        router = actor("router", GREY_B, RX, w=2.4)
        issuer = actor("card issuer", GREEN_M, IX, sub="api.pay.test")
        wl = Line([CX + 1.65, AY, 0], [RX - 1.2, AY, 0], stroke_width=3, color=GREY_D)
        wr = Line([RX + 1.2, AY, 0], [IX - 1.65, AY, 0], stroke_width=3, color=GREY_D)
        req = msg("amount=100.00", WHITE, CX, mono=True)
        self.steps("Your checkout service sends a payment to a card issuer, across a router you don't own. "
                   "What stops the router from reading it?", [
            (lambda: [FadeIn(client)], 0.6),
            "a card issuer",
            (lambda: [FadeIn(issuer)], 0.6),
            "across a router",
            (lambda: [Create(wl), Create(wr), FadeIn(router)], 0.8),
            (lambda: [FadeIn(req, scale=0.9)], 0.3),
            (lambda: [req.animate.move_to(at(req, RX))], 1.0),
            "What stops",
            (lambda: [glow(router[0], YELLOW_M, 1.05)], 0.9),
        ])

        seen_h = rl("the router sees", 0, GREY_B)
        seen1 = rl("amount=100.00", 1, YELLOW_M, 24, mono=True)
        req9 = msg("amount=900.00", RED_M, RX, mono=True)
        charged = il("charges 900.00", 0, RED_M)
        self.steps("Nothing. It reads every byte, and it can change 100 to 900 and pass the request on.", [
            (lambda: [FadeIn(seen_h), FadeIn(seen1, shift=0.1 * DOWN)], 0.7),
            "it can change",
            (lambda: [Transform(req, req9)], 0.6),
            "and pass",
            (lambda: [req.animate.move_to(at(req, IX))], 0.8),
            (lambda: [FadeIn(charged)], 0.5),
        ])

        key = msg("key", GOLD_M, CX)
        copied = rl("the key, copied", 1, GOLD_M)
        xk = tick(False, 0.22).move_to([RX + 0.9, LANE, 0])
        self.steps("Encryption needs a key both ends share. Sending it doesn't work: the router would copy it.", [
            (lambda: [FadeOut(req), FadeOut(charged), FadeOut(seen1)], 0.6),
            "Sending it",
            (lambda: [FadeIn(key, scale=0.8)], 0.3),
            (lambda: [key.animate.move_to(at(key, RX))], 0.8),
            "the router would",
            (lambda: [FadeIn(copied, shift=0.1 * DOWN)], 0.5),
            (lambda: [Create(xk)], 0.4),
        ])

        c_sec = cl("secret: 6", 0, GOLD_M)
        c_pub = cl("5^6 mod 23 = 8", 1, GREY_B, 24, mono=True)
        pub = rl("public: 5 and 23", 1, GREY_B)
        ch = msg("ClientHello: key share 8", BLUE_M, CX)
        r_8 = rl("key share 8", 2, YELLOW_M)
        self.steps("So each side keeps a secret, and sends only a number made from it. "
                   "The client keeps 6, and sends 8 in its first message, the ClientHello.", [
            (lambda: [FadeOut(key), FadeOut(xk), FadeOut(copied)], 0.5),
            "The client keeps",
            (lambda: [FadeIn(c_sec, shift=0.1 * DOWN), FadeIn(pub)], 0.6),
            "and sends 8",
            (lambda: [FadeIn(c_pub, shift=0.1 * DOWN), FadeIn(ch, scale=0.9)], 0.5),
            (lambda: [ch.animate.move_to(at(ch, RX))], 0.7),
            (lambda: [FadeIn(r_8)], 0.3),
            (lambda: [ch.animate.move_to(at(ch, IX))], 0.7),
        ])

        i_sec = il("secret: 15", 0, GOLD_M)
        i_pub = il("5^15 mod 23 = 19", 1, GREY_B, 24, mono=True)
        sh = msg("ServerHello: key share 19", GREEN_M, IX)
        r_19 = rl("key share 19", 3, YELLOW_M)
        self.steps("The issuer keeps 15, and answers 19 in its ServerHello.", [
            (lambda: [FadeOut(ch), FadeIn(i_sec, shift=0.1 * DOWN)], 0.5),
            "and answers",
            (lambda: [FadeIn(i_pub, shift=0.1 * DOWN), FadeIn(sh, scale=0.9)], 0.5),
            (lambda: [sh.animate.move_to(at(sh, RX))], 0.7),
            (lambda: [FadeIn(r_19)], 0.3),
            (lambda: [sh.animate.move_to(at(sh, CX))], 0.7),
        ])

        c_mix = cl("19^6 mod 23 = 2", 2, GREY_B, 24, mono=True)
        i_mix = il("8^15 mod 23 = 2", 2, GREY_B, 24, mono=True)
        c_key = cl("key: 2", 3, GREEN_M, 28)
        i_key = il("key: 2", 3, GREEN_M, 28)
        r_key = rl("key: no way to compute it", 4, RED_M)
        self.steps("Each side mixes the other's number with its own secret, and both get 2. The router saw 8 and 19. "
                   "With real 32-byte numbers, it can't get from those to the key.", [
            (lambda: [FadeOut(sh), FadeIn(c_mix, shift=0.1 * DOWN), FadeIn(i_mix, shift=0.1 * DOWN)], 0.8),
            "and both get 2",
            (lambda: [FadeIn(c_key, scale=1.2), FadeIn(i_key, scale=1.2)], 0.6),
            "The router saw",
            (lambda: [Indicate(r_8, color=YELLOW_M), Indicate(r_19, color=YELLOW_M)], 0.9),
            "With real",
            (lambda: [FadeIn(r_key, shift=0.1 * DOWN)], 0.6),
        ])

        rtrip = DoubleArrow([CX + 1.4, LANE, 0], [IX - 1.4, LANE, 0], buff=0, stroke_width=3, color=GREY_B,
                            max_tip_length_to_length_ratio=0.04)
        rtl = T("one round trip", 24, GREY_B).move_to([RX, LANE, 0])
        rtl_bg = BackgroundRectangle(rtl, color=BLACK, fill_opacity=1, buff=0.15).set_z_index(2)
        rtl.set_z_index(3)
        enc_l = T("encrypted", 20, GOLD_M).move_to([(CX + 1.65 + RX - 1.2) / 2, AY + 0.32, 0])
        enc_r = T("encrypted", 20, GOLD_M).move_to([(RX + 1.2 + IX - 1.65) / 2, AY + 0.32, 0])
        self.steps("That took one round trip. Everything after the ServerHello is encrypted with that key.", [
            (lambda: [GrowFromCenter(rtrip), FadeIn(rtl_bg), FadeIn(rtl)], 0.8),
            "Everything after",
            (lambda: [wl.animate.set_stroke(GOLD_M, 5), wr.animate.set_stroke(GOLD_M, 5), FadeIn(enc_l), FadeIn(enc_r)], 0.8),
            (lambda: [FadeOut(VGroup(rtrip, rtl_bg, rtl, c_sec, c_pub, c_mix, i_sec, i_pub, i_mix, pub, r_8, r_19, r_key)),
                      c_key.animate.move_to(cl("key: 2", 0, size=28)), i_key.animate.move_to(il("key: 2", 0, size=28))], 0.8),
        ])

        ka = T("key A", 20, RED_M).move_to(enc_l)
        kb = T("key B", 20, RED_M).move_to(enc_r)
        c_keyA = cl("key A (the router has it)", 0, RED_M)
        i_keyB = il("key B", 0, RED_M)
        r_ab = rl("holds key A and key B", 1, RED_M)
        self.steps("But the router could play both parts, with one exchange on each side, passing messages between them. "
                   "You'd have an encrypted line to the attacker.", [
            "play both parts",
            (lambda: [router[0].animate.set_stroke(RED_M).set_fill(fillc(RED_M), 1)], 0.6),
            "with one exchange",
            (lambda: [Transform(enc_l, ka), Transform(c_key, c_keyA), wl.animate.set_stroke(RED_M)], 0.5),
            (lambda: [Transform(enc_r, kb), Transform(i_key, i_keyB), wr.animate.set_stroke(RED_M)], 0.5),
            "passing messages",
            (lambda: [FadeIn(r_ab, shift=0.1 * DOWN), flow(wl, RED_M, 0.6)], 0.7),
            (lambda: [flow(wr, RED_M, 0.6)], 0.7),
            "You'd have",
            (lambda: [glow(client[0], RED_M, 1.04)], 0.9),
        ])

        leaf = cert("api.pay.test", "Pay Test CA", IX, -0.15, key="public key 3f a2 91 …")
        crt = msg("Certificate", GOLD_M, IX)
        r_enc = rl("encrypted bytes", 1, GOLD_M)
        leaf_c = cert("api.pay.test", "Pay Test CA", CX, -0.15, key="public key 3f a2 91 …")
        self.steps("So the issuer proves who it is. It sends a certificate: this public key belongs to api.pay.test, "
                   "signed by a certificate authority.", [
            (lambda: [router[0].animate.set_stroke(GREY_B).set_fill(fillc(GREY_B), 1), FadeOut(r_ab),
                      Transform(enc_l, T("encrypted", 20, GOLD_M).move_to(enc_l)),
                      Transform(enc_r, T("encrypted", 20, GOLD_M).move_to(enc_r)),
                      Transform(c_key, cl("key: 2", 0, GREEN_M, 28)), Transform(i_key, il("key: 2", 0, GREEN_M, 28)),
                      wl.animate.set_stroke(GOLD_M), wr.animate.set_stroke(GOLD_M)], 0.8),
            "It sends",
            (lambda: [FadeIn(leaf, shift=0.1 * DOWN)], 0.6),
            (lambda: [FadeIn(crt, scale=0.9)], 0.3),
            (lambda: [crt.animate.move_to(at(crt, RX))], 0.7),
            (lambda: [FadeIn(r_enc)], 0.3),
            (lambda: [crt.animate.move_to(at(crt, CX))], 0.7),
            (lambda: [FadeOut(crt), FadeIn(leaf_c, shift=0.1 * DOWN)], 0.5),
        ])

        mid = cert("Pay Test CA", "Root CA", CX, -1.75)
        a1 = Arrow([CX, -0.81, 0], [CX, -1.29, 0], buff=0, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.35)
        store = RoundedRectangle(corner_radius=0.12, width=3.3, height=0.8, stroke_color=GREY_B, stroke_width=2).move_to([CX, -3.05, 0])
        store_l = T("trust store", 22, GREY_B).move_to([CX - 0.8, -3.05, 0])
        root = chip("Root CA", GREEN_M, 22).move_to([CX + 0.7, -3.05, 0])
        a2 = Arrow([CX, -2.21, 0], [CX, -2.63, 0], buff=0, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.35)
        t1 = tick(True, 0.15).move_to([CX + 0.45, -1.05, 0])
        t2 = tick(True, 0.15).move_to([CX + 0.45, -2.42, 0])
        self.steps("The client walks up the chain. The authority's certificate came along, signed by a root "
                   "that is already in the client's trust store.", [
            (lambda: [glow(leaf_c[0], GREEN_M, 1.04)], 0.7),
            "The authority's",
            (lambda: [GrowArrow(a1), FadeIn(mid, shift=0.1 * DOWN)], 0.7),
            (lambda: [Create(t1)], 0.4),
            "signed by a root",
            (lambda: [GrowArrow(a2)], 0.5),
            "already in",
            (lambda: [Create(store), FadeIn(store_l), FadeIn(root)], 0.7),
            (lambda: [Create(t2), glow(root[0], GREEN_M, 1.08)], 0.7),
        ])

        pk = chip("private key", GOLD_M, 24)
        pk.move_to([IL + pk.width / 2, -1.75, 0])
        pk_n = il("never leaves the issuer", 4, GREY_B, 22).shift(0.5 * DOWN)
        sig = msg("signature over the handshake", GOLD_M, IX)
        t3 = tick(True, 0.18).move_to([CX + 1.95, -0.15, 0])
        self.steps("Anyone can copy a certificate. So the issuer also signs the whole handshake with its private key, "
                   "which never leaves the issuer.", [
            (lambda: [glow(leaf[0], GREY_B, 1.04)], 0.8),
            "So the issuer",
            (lambda: [FadeIn(pk, scale=0.9)], 0.5),
            (lambda: [FadeIn(sig, scale=0.9)], 0.3),
            (lambda: [sig.animate.move_to(at(sig, RX))], 0.7),
            (lambda: [sig.animate.move_to(at(sig, CX))], 0.7),
            "which never leaves",
            (lambda: [FadeIn(pk_n), FadeOut(sig), Create(t3)], 0.6),
        ])

        r_has = rl("a copy of the certificate", 1, GREY_B)
        r_no = rl("no private key", 2, RED_M)
        fake = msg("fake signature", RED_M, RX)
        x3 = tick(False, 0.18).move_to([CX + 1.95, -0.15, 0])
        closed = T("closed", 20, RED_M).move_to(enc_l)
        self.steps("An attacker in the router has the certificate, but not that key. It can't make the signature, "
                   "so the check fails, and the client hangs up.", [
            (lambda: [router[0].animate.set_stroke(RED_M).set_fill(fillc(RED_M), 1), FadeOut(t3), FadeOut(r_enc)], 0.6),
            (lambda: [FadeIn(r_has, shift=0.1 * DOWN)], 0.5),
            "but not that key",
            (lambda: [FadeIn(r_no, shift=0.1 * DOWN)], 0.5),
            "It can't make",
            (lambda: [FadeIn(fake, scale=0.9)], 0.3),
            (lambda: [fake.animate.move_to(at(fake, CX))], 0.8),
            "so the check fails",
            (lambda: [Create(x3), FadeOut(fake)], 0.5),
            "and the client hangs up",
            (lambda: [wl.animate.set_stroke(RED_M, 2).set_opacity(0.4), Transform(enc_l, closed)], 0.7),
        ])

        rec = msg("a9 4f 1c 70 … tag 9c e1", GOLD_M, CX, size=20, mono=True)
        rec_bad = chip("a9 4f 1d 70 … tag 9c e1", RED_M, 20, mono=True)
        rec_bad.move_to(at(rec_bad, RX))
        r_rand = rl("random-looking bytes", 1, GOLD_M)
        r_flip = rl("flips one bit", 2, RED_M)
        i_fail = il("tag check fails", 2, RED_M)
        i_drop = il("record rejected", 3, RED_M)
        self.steps("Every record is now encrypted, with a 16-byte tag. Flip one bit on the way, and the check fails.", [
            (lambda: [FadeOut(VGroup(leaf_c, mid, a1, a2, t1, t2, x3, store, store_l, root, pk, pk_n, leaf, r_has, r_no)),
                      router[0].animate.set_stroke(GREY_B).set_fill(fillc(GREY_B), 1),
                      wl.animate.set_stroke(GOLD_M, 5).set_opacity(1), Transform(enc_l, T("encrypted", 20, GOLD_M).move_to(enc_l))], 0.8),
            (lambda: [FadeIn(rec, scale=0.9)], 0.3),
            (lambda: [rec.animate.move_to(at(rec, RX))], 0.7),
            (lambda: [FadeIn(r_rand)], 0.4),
            "Flip one bit",
            (lambda: [Transform(rec, rec_bad), FadeIn(r_flip)], 0.5),
            (lambda: [rec.animate.move_to(at(rec, IX))], 0.7),
            "and the check",
            (lambda: [FadeIn(i_fail), FadeIn(i_drop)], 0.5),
        ])

        sees = VGroup(rl("both IP addresses", 1), rl("record sizes and timing", 2), rl("the server name, api.pay.test", 3))
        can = rl("it can drop packets", 4, GREY_B)
        cant = rl("it can't read or change them", 5, GREEN_M)
        self.steps("The router still sees addresses, record sizes and the server name, and it can drop packets. "
                   "It can't read or change a byte.", [
            (lambda: [FadeOut(VGroup(rec, r_rand, r_flip, i_fail, i_drop))], 0.5),
            (lambda: [LaggedStart(*[FadeIn(s, shift=0.1 * DOWN) for s in sees], lag_ratio=0.5)], 1.6),
            "and it can drop",
            (lambda: [FadeIn(can, shift=0.1 * DOWN)], 0.5),
            "It can't read",
            (lambda: [FadeIn(cant, shift=0.1 * DOWN)], 0.6),
        ])

        self.steps("One round trip agrees a key nobody on the path can compute. "
                   "A chain to a root you trust proves who holds the other end.", [
            (lambda: [Indicate(c_key, color=GREEN_M), Indicate(i_key, color=GREEN_M)], 1.0),
            (lambda: [wl.animate(rate_func=there_and_back).set_stroke(width=9),
                      wr.animate(rate_func=there_and_back).set_stroke(width=9)], 1.0),
            "A chain",
            (lambda: [glow(issuer[0], GREEN_M, 1.05)], 1.0),
        ])
        self.wait(0.6)
