from sfz import *

# Applied in this order, before the course-wide rules.
SAY[0:0] = [
    (r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b", r"\1 dot \2 dot \3 dot \4"),
    (r"\b192 dot 168\b", "one ninety-two dot one sixty-eight"),
    (r"\b192\.168\b", "one ninety-two dot one sixty-eight"),
    (r"\b172\.16\b", "one seventy-two dot sixteen"),
    (r"\b172\.31\b", "one seventy-two dot thirty-one"),
    (r"\b41000\b", "forty-one thousand"),
    (r"\b3417\b", "thirty-four seventeen"),
    (r"\b8080\b", "eighty eighty"),
]

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
CL, PR = np.array([-5.35, 1.55, 0]), np.array([-5.35, 0.2, 0])   # inside: client and peer
RT = np.array([-1.0, 0.875, 0])                                   # the router, one foot on each side
SV = np.array([5.2, 0.875, 0])                                    # outside: the server
CW, CH = 2.3, 0.9
RW, RH = 2.7, 1.5
SW_, SH = 2.5, 1.25
CARD_A = np.array([-3.0, 3.05, 0])    # a packet as it looks inside
CARD_B = np.array([2.15, 2.05, 0])    # the same packet outside
CARD_W, CARD_H = 3.1, 0.85
TB_Y = [-1.65, -2.05, -2.45]          # rows of the router's table
COL_X = [-3.6, 0.2, 3.9]              # inside, outside, far end
CAP_Y, BAR_Y = -3.0, -3.42

W_CL = [CL + [CW / 2, 0, 0], RT + [-RW / 2, 0.33, 0]]
W_PR = [PR + [CW / 2, 0, 0], RT + [-RW / 2, -0.33, 0]]
W_OUT = [RT + [RW / 2, 0, 0], SV + [-SW_ / 2, 0, 0]]


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
        if t > dur + 0.1:
            print(f"WARNING: steps run {t - dur:.1f}s past the line: {text[:50]}")
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 12.6).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def swap(old, new, d=UP):
    """Replace one label with another: the old one leaves before the new one arrives, so they never overlap."""
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def run(pts, color=YELLOW_M, rt=0.9, frac=1.0):
    """A dot (a packet) running along a wire; frac < 1 stops part of the way and leaves the dot there."""
    a, b = np.array(pts[0]), np.array(pts[1])
    d = Dot(radius=0.09, color=color).move_to(a).set_z_index(3)
    seq = [FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(a, a + frac * (b - a)), rate_func=smooth, run_time=rt)]
    if frac >= 1:
        seq.append(FadeOut(d, run_time=0.12))
    return d, Succession(*seq)


def go(pts, color=YELLOW_M, rt=0.9):
    return run(pts, color, rt)[1]


def back(pts):
    return list(reversed(pts))


# ---- the pieces ----
def node(lines, c, w, h, color=WHITE):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(BLACK, 1).move_to(c)
    g = VGroup(*lines).arrange(DOWN, buff=0.12).move_to(c)
    return VGroup(r, *g)


def card(lines, c, color=WHITE):
    r = RoundedRectangle(corner_radius=0.1, width=CARD_W, height=CARD_H, stroke_color=color, stroke_width=2.5)
    r.set_fill(fillc(color, 0.12), 1).move_to(c)
    return VGroup(r, VGroup(*lines).arrange(DOWN, buff=0.12, aligned_edge=LEFT).move_to(c))


def pk(frm, to, hl=None, hc=YELLOW_M):
    """Two lines of a packet header; hl ('from' or 'to') is drawn in colour hc."""
    return [M(f"from {frm}", 15, hc if hl == "from" else WHITE), M(f"to {to}", 15, hc if hl == "to" else WHITE)]


def cell(s, k, row, color=WHITE, mono=True):
    t = M(s, 17, color) if mono else T(s, 19, color)
    return t.move_to([COL_X[k], TB_Y[row], 0])


class Nat(Base):
    """net-03, section 2. Three devices at home share one internet address. Private blocks can't be answered from outside,
    so the router rewrites the source to its own outside address and writes the connection in a table (the mailroom's
    ledger). Two connections from port 41000 would collide, so it rewrites the port too (3417). Costs: nothing gets in
    without a line, and quiet lines are crossed out without telling anyone."""

    def set_card(self, which, lines, color=WHITE):
        new = card(lines, CARD_A if which == "A" else CARD_B, color)
        old = self.cards[which]
        self.cards[which] = new
        return [swap(old, new)]

    def clear_cards(self):
        out = [FadeOut(c) for c in self.cards.values() if c is not None]
        self.cards = {"A": None, "B": None}
        return out

    def construct(self):
        self.capm = None
        self.cards = {"A": None, "B": None}
        self.title_card("One address, many computers", "how a home router shares one address, and what it must remember")

        # ---------------- scene 1: the hook ----------------
        phone = node([T("your phone", 24), M("192.168.1.23", 20)], [-4.3, 0.6, 0], 3.0, 1.2)
        site = node([T("a website", 24), T("you're calling from:", 18, GREY_B), M("one other address", 18, YELLOW_M)], [4.3, 0.6, 0], 3.4, 1.5)
        others = VGroup(node([T("laptop", 20)], [-4.3, -1.05, 0], 1.7, 0.6), node([T("TV", 20)], [-2.35, -1.05, 0], 1.0, 0.6))
        hw = Line([-2.8, 0.6, 0], [2.6, 0.6, 0], stroke_width=2.5, color=GREY_B).set_z_index(-5)
        self.steps("Look at your phone's Wi-Fi settings at home. It shows an IP address, such as 192.168.1.23.", [
            (lambda: [FadeIn(phone, shift=0.2 * UP)], 0.8),
            "such as",
            (lambda: [Indicate(phone[2], color=YELLOW_M, scale_factor=1.1)], 0.8),
        ])
        self.steps("Now ask a website which address you're calling from. You get a different one: the same one your laptop and TV get.", [
            "Now ask",
            (lambda: [Create(hw), FadeIn(site, shift=0.2 * UP)], 0.9),
            "You get a different",
            (lambda: [Indicate(site[3], color=YELLOW_M, scale_factor=1.1)], 0.8),
            "your laptop",
            (lambda: [FadeIn(others, shift=0.1 * UP)], 0.6),
        ])
        self.steps("Three devices share one address on the internet. Yet the film goes to the TV, and the messages to your phone. "
                   "How does the box on the wall keep them apart?", [
            "Yet the film",
            (lambda: [glow(others[1][0], WHITE, 1.08)], 0.7),
            "and the messages",
            (lambda: [glow(phone[0], WHITE, 1.05)], 0.7),
            "How does",
            (lambda: self.cap("three devices, one address: how do the replies find the right one?", WHITE), 0.5),
        ])
        self.steps("And here's the odd part. Millions of homes use 192.168.1.23 right now.", [
            "Millions of homes",
            (lambda: self.cap("millions of homes use 192.168.1.23 right now", YELLOW_M), 0.5),
        ])

        # ---------------- scene 2: why private addresses ----------------
        self.steps("Start with a counting problem. An IP address has 32 bits, so there are about 4.3 billion of them. "
                   "Today there are more mobile phone contracts in the world than that.", [
            (lambda: [FadeOut(VGroup(phone, site, others, hw)), *self.cap("32 bits: about 4.3 billion addresses")], 0.8),
            "Today there are",
            (lambda: self.cap("more mobile phone contracts than IPv4 addresses"), 0.5),
        ])
        blocks = VGroup(*[M(s, 26, GREEN_M) for s in ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]]).arrange(RIGHT, buff=0.9)
        blocks.move_to([0, 0.9, 0])
        bnote = T("private: use them inside, as often as you like", 22, GREY_B).move_to([0, 0.2, 0])
        self.steps("So three blocks were set aside for private use: addresses starting with 10, with 172.16 to 172.31, "
                   "and with 192.168.", [
            (lambda: self.uncap(), 0.3),
            "three blocks",
            (lambda: [LaggedStart(*[FadeIn(b, shift=0.1 * UP) for b in blocks], lag_ratio=0.4)], 1.4),
        ])
        self.steps("Anyone may use them inside their own network, as many times over as they like, and no router on the internet "
                   "carries packets to them.", [
            (lambda: [FadeIn(bnote)], 0.5),
            "no router on",
            (lambda: self.cap("no router on the internet carries packets to them", RED_M), 0.5),
        ])

        # ---------------- the lab network ----------------
        cl = node([T("client", 22), M("10.10.1.10", 16)], CL, CW, CH)
        pr = node([T("peer", 22), M("10.10.1.20", 16)], PR, CW, CH)
        rt = node([T("router", 24), M("inside 10.10.1.2", 15, GREY_B), M("outside 10.10.2.2", 15, YELLOW_M)], RT, RW, RH, GREY_B)
        sv = node([T("server", 22), M("10.10.2.20", 16), M("port 8080", 15, GREY_B)], SV, SW_, SH)
        wires = VGroup(*[Line(*w, stroke_width=2.5, color=GREY_B).set_z_index(-5) for w in (W_CL, W_PR, W_OUT)])
        inside_l = T("inside", 20, GREY_B).move_to(CL + [0, 0.72, 0])
        outside_l = T("outside", 20, GREY_B).move_to(SV + [0, 0.95, 0])
        self.steps("Let's watch it on the lab network. Inside, client and peer have private addresses. Outside sits a server. "
                   "In between, a router, with one address on each side.", [
            (lambda: [*self.uncap(), FadeOut(blocks), FadeOut(bnote)], 0.5),
            "Inside, client",
            (lambda: [FadeIn(cl), FadeIn(pr), FadeIn(inside_l)], 0.7),
            "Outside sits",
            (lambda: [FadeIn(sv), FadeIn(outside_l)], 0.6),
            "In between",
            (lambda: [FadeIn(rt), Create(wires)], 0.8),
            "one address on each",
            (lambda: [Indicate(rt[2], color=WHITE, scale_factor=1.1), Indicate(rt[3], color=YELLOW_M, scale_factor=1.1)], 0.8),
        ])

        # ---------------- scene 3: the reply with nowhere to go ----------------
        self.steps("Client opens a connection to the server, from port 41000 to port 8080. A port is the number that picks one program on a computer.", [
            (lambda: [*self.set_card("A", pk("10.10.1.10:41000", "10.10.2.20:8080"))], 0.6),
            "A port is",
            (lambda: self.cap("a port: the number that picks one program on a computer"), 0.5),
        ])
        stuck, stuck_go = run(back(W_OUT), WHITE, 0.8, frac=0.5)
        nox = tick(False, 0.15).move_to((np.array(W_OUT[0]) + np.array(W_OUT[1])) / 2)
        nor = T("no way back to 10.10.1.10", 18, RED_M).move_to(nox.get_center() + 0.4 * DOWN)
        self.steps("The question gets there. But the answer is addressed to 10.10.1.10, and the server has no way back to it.", [
            (lambda: [*self.uncap(), go(W_CL)], 0.7),
            (lambda: [go(W_OUT), *self.set_card("B", pk("10.10.1.10:41000", "10.10.2.20:8080"))], 0.9),
            "But the answer",
            (lambda: [*self.set_card("B", pk("10.10.2.20:8080", "10.10.1.10:41000", "to", RED_M))], 0.6),
            (lambda: [stuck_go], 0.8),
            (lambda: [FadeOut(stuck, scale=1.8), Create(nox), FadeIn(nor)], 0.5),
        ])
        self.steps("Out on the internet, no router could even tell which of a million homes you mean. "
                   "What we need is someone at the door who takes each reply to the right desk.", [
            "What we need",
            (lambda: self.cap("the wish: someone at the door who takes each reply to the right desk", WHITE), 0.5),
        ])

        # ---------------- scene 4: the mailroom ----------------
        self.steps("Think of an office building with one street address. Every letter leaves through the mailroom, "
                   "which writes the building's address as the return address.", [
            (lambda: [*self.uncap(), *self.clear_cards(), FadeOut(nox), FadeOut(nor)], 0.5),
            "one street address",
            (lambda: [Indicate(rt[3], color=YELLOW_M, scale_factor=1.12)], 0.8),
            "the mailroom",
            (lambda: [glow(rt[0], GREY_B, 1.04)], 0.7),
        ])
        self.steps("Replies come back to the mailroom, and a clerk walks each one to the desk that sent the original.", [
            (lambda: [go(back(W_OUT), WHITE, 0.8)], 0.8),
            "walks each one",
            (lambda: [go(back(W_CL), WHITE, 0.7)], 0.7),
        ])
        mail_t = T("the mailroom", 18, GREY_B).move_to(RT + [0, RH / 2 + 0.3, 0])
        desks_t = T("inside: the desks", 20, GREY_B).move_to(inside_l)
        self.steps("Map it. The mailroom is the router. The desks are the computers inside. "
                   "And the building's street address is the router's outside address, 10.10.2.2.", [
            "The mailroom is",
            (lambda: [FadeIn(mail_t, shift=0.1 * DOWN)], 0.5),
            "The desks are",
            (lambda: [swap(inside_l, desks_t)], 0.6),
            "the building's street",
            (lambda: [Indicate(rt[3], color=YELLOW_M, scale_factor=1.12), *self.cap("the building's address = the router's outside address, 10.10.2.2")], 0.8),
        ])

        # ---------------- scene 5: rewrite and write it down ----------------
        heads = VGroup(*[T(s, 18, GREY_B).move_to([x, -1.2, 0]) for s, x in zip(["inside", "outside", "far end"], COL_X)])
        rule = Line([-5.6, -1.4, 0], [5.6, -1.4, 0], stroke_width=1.5, color=GREY_C)
        tb_t = left_at(T("the router's table", 20, GREY_B), -5.6, -0.8)
        row1 = VGroup(cell("10.10.1.10:41000", 0, 0), cell("10.10.2.2:41000", 1, 0, YELLOW_M), cell("10.10.2.20:8080", 2, 0))
        self.steps("So the router rewrites the source of every packet going out, to its own outside address.", [
            (lambda: [*self.uncap(), *self.set_card("A", pk("10.10.1.10:41000", "10.10.2.20:8080"))], 0.6),
            (lambda: [go(W_CL)], 0.7),
            "rewrites the source",
            (lambda: [*self.set_card("B", pk("10.10.2.2:41000", "10.10.2.20:8080", "from"))], 0.7),
        ])
        self.steps("And before the packet leaves, it writes down what it did: the inside address and port, the outside ones, "
                   "and the far end.", [
            "writes down",
            (lambda: [FadeIn(tb_t), FadeIn(heads), Create(rule)], 0.6),
            "the inside address",
            (lambda: [FadeIn(row1[0], shift=0.1 * DOWN)], 0.3),
            "the outside ones",
            (lambda: [FadeIn(row1[1], shift=0.1 * DOWN)], 0.3),
            "the far end",
            (lambda: [FadeIn(row1[2], shift=0.1 * DOWN), go(W_OUT)], 0.6),
        ])
        self.steps("The server sees a packet from 10.10.2.2, an address on its own network, so it can answer.", [
            "it can answer",
            (lambda: [*self.set_card("B", pk("10.10.2.20:8080", "10.10.2.2:41000", "to")), go(back(W_OUT), WHITE, 0.8)], 0.8),
        ])
        self.steps("The router finds the line, rewrites the destination back to 10.10.1.10, and sends it inside.", [
            "finds the line",
            (lambda: [Indicate(row1, color=YELLOW_M, scale_factor=1.04)], 0.8),
            "rewrites the destination",
            (lambda: [*self.set_card("A", pk("10.10.2.20:8080", "10.10.1.10:41000", "to", GREEN_M))], 0.6),
            "sends it inside",
            (lambda: [go(back(W_CL), GREEN_M, 0.7)], 0.7),
        ])
        self.steps("This is NAT: network address translation.", [
            (lambda: self.cap("NAT, network address translation: rewrite on the way out, rewrite back on the way in", WHITE), 0.6),
        ], after=0.5)

        # ---------------- scene 6: two connections, one port ----------------
        row2 = VGroup(cell("10.10.1.20:41000", 0, 1), cell("10.10.2.2:41000", 1, 1, RED_M), cell("10.10.2.20:8080", 2, 1))
        self.steps("Now peer connects too: same server, and by chance, the same port, 41000. If the router rewrites only the address, "
                   "what will peer's packet look like outside? Pause and guess.", [
            (lambda: [*self.uncap(), *self.set_card("A", pk("10.10.1.20:41000", "10.10.2.20:8080")), FadeOut(self.cards["B"])], 0.6),
            (lambda: [go(W_PR)], 0.7),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.cards["B"] = None
        self.countdown(3.0)
        self.steps("Exactly like client's: 10.10.2.2, port 41000, to the same server. "
                   "So when an answer comes back to port 41000, whose is it? The router can't tell.", [
            (lambda: [*self.uncap(), *self.set_card("B", pk("10.10.2.2:41000", "10.10.2.20:8080", "from", RED_M)),
                      FadeIn(row2, shift=0.1 * DOWN)], 0.7),
            (lambda: [Indicate(row1[1], color=RED_M, scale_factor=1.12), Indicate(row2[1], color=RED_M, scale_factor=1.12)], 0.9),
            "whose is it",
            (lambda: [*self.set_card("B", pk("10.10.2.20:8080", "10.10.2.2:41000", "to", RED_M)), go(back(W_OUT), WHITE, 0.8)], 0.8),
            "The router can't",
            (lambda: [*self.cap("two lines, same outside port: the reply could be either", RED_M), glow(rt[0], RED_M, 1.04)], 0.7),
        ])
        r2fix = cell("10.10.2.2:3417", 1, 1, YELLOW_M)
        self.steps("So the router rewrites the port too. It gives peer's connection a different outside port. In the lesson's run, it picked 3417.", [
            (lambda: [*self.uncap(), *self.set_card("A", pk("10.10.1.20:41000", "10.10.2.20:8080"))], 0.5),
            "rewrites the port",
            (lambda: [*self.set_card("B", pk("10.10.2.2:3417", "10.10.2.20:8080", "from"))], 0.6),
            "it picked 3417",
            (lambda: [swap(row2[1], r2fix)], 0.6),
        ])
        row2[1] = r2fix
        self.steps("Now every line is different, and every answer can be matched. "
                   "In the mailroom, the ledger says: replies for 41000 go to client, replies for 3417 go to peer.", [
            (lambda: [row1[1].animate.set_color(WHITE), row2[1].animate.set_color(WHITE)], 0.5),
            "replies for 41000",
            (lambda: [Indicate(row1, color=YELLOW_M, scale_factor=1.04), go(back(W_CL), WHITE, 0.7)], 0.8),
            "replies for 3417",
            (lambda: [Indicate(row2, color=YELLOW_M, scale_factor=1.04), go(back(W_PR), WHITE, 0.7)], 0.8),
        ])
        self.steps("Nearly every NAT you'll meet works this way. Linux calls its version masquerade.", [
            (lambda: self.cap("one line per connection, addresses and ports  (Linux: MASQUERADE)", WHITE), 0.5),
        ])
        self.steps("And the server? As far as it knows, it's chatting with one very busy computer.", [
            "As far as",
            (lambda: [glow(sv[0], WHITE), Indicate(rt[3], color=YELLOW_M, scale_factor=1.12)], 0.8),
        ], after=0.5)

        # ---------------- scene 7: two costs ----------------
        self.steps("This trick has two costs. First, nothing outside can start a conversation. "
                   "A packet that arrives unasked matches no line, so it goes nowhere.", [
            (lambda: [*self.uncap(), *self.clear_cards()], 0.4),
            "nothing outside",
            (lambda: [*self.set_card("B", [T("new, from outside", 18, RED_M), M("to 10.10.2.2:41000", 15)], RED_M),
                      *self.cap("cost 1: nothing outside can start a conversation in")], 0.6),
            "arrives unasked",
            (lambda: [go(back(W_OUT), RED_M, 0.8)], 0.8),
            (lambda: [glow(rt[0], RED_M, 1.04)], 0.6),
        ])
        strike = Line([-5.0, TB_Y[0], 0], [5.0, TB_Y[0], 0], stroke_width=3, color=RED_M)
        self.steps("Second, the table can't grow forever, so a line that stays quiet for too long is crossed out. Neither end is told.", [
            (lambda: [*self.clear_cards(), *self.cap("cost 2: quiet lines are crossed out, and nobody is told")], 0.5),
            "crossed out",
            (lambda: [Create(strike), row1.animate.set_opacity(0.3)], 0.7),
        ])
        dead, dead_go = run(W_OUT, WHITE, 0.6, frac=0.25)
        nox2 = tick(False, 0.15).move_to(np.array(W_OUT[0]) * 0.75 + np.array(W_OUT[1]) * 0.25)
        self.steps("Client still thinks its connection is open. Its next packet matches nothing, and is dropped.", [
            (lambda: [*self.set_card("A", pk("10.10.1.10:41000", "10.10.2.20:8080"))], 0.5),
            (lambda: [go(W_CL)], 0.7),
            "matches nothing",
            (lambda: [dead_go], 0.6),
            (lambda: [FadeOut(dead, scale=1.8), Create(nox2),
                      self.cards["A"][0].animate.set_stroke(RED_M)], 0.5),
        ])
        self.steps("The next section shows how long routers wait, and what to do about it.", [
            (lambda: self.cap("how long a router waits: the next section"), 0.5),
        ])

        # ---------------- scene 8: the moral, and a check ----------------
        r1 = VGroup(cell("10.10.1.10:41000", 0, 0), cell("10.10.2.2:41000", 1, 0), cell("10.10.2.20:8080", 2, 0))
        self.steps("So how does the film find the TV? The router wrote it down: one line per conversation, "
                   "rewritten on the way out and on the way back.", [
            (lambda: [*self.uncap(), *self.clear_cards(), FadeOut(nox2)], 0.3),
            (lambda: [FadeOut(strike), FadeOut(row1), FadeIn(r1)], 0.6),
            "one line per",
            (lambda: [*self.cap("one line per conversation, rewritten on the way out and on the way back", WHITE),
                      Indicate(VGroup(r1, row2), color=YELLOW_M, scale_factor=1.03)], 0.9),
        ])
        q3 = VGroup(cell("a third computer, port 41000", 0, 2, WHITE, mono=False), cell("?", 1, 2, YELLOW_M), cell("10.10.2.20:8080", 2, 2))
        self.steps("One quick check. A third computer inside connects to the same server, also from port 41000. "
                   "What does the router do? Pause and think.", [
            "A third computer",
            (lambda: [FadeIn(q3, shift=0.1 * DOWN)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        q3fix = cell("10.10.2.2: another free port", 1, 2, GREEN_M, mono=False)
        self.steps("It picks another free outside port, and writes a third line.", [
            (lambda: [*self.uncap(), swap(q3[1], q3fix)], 0.6),
            "writes a third",
            (lambda: [Indicate(VGroup(q3[0], q3fix, q3[2]), color=GREEN_M, scale_factor=1.04)], 0.8),
        ], after=0.3)
        self.play(*self.cap("one address outside, one line per conversation inside the router", YELLOW_M, 26), run_time=0.6)
        self.wait(2.0)
