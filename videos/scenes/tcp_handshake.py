from sfz import *
import random

# Amounts are said the way people say them; the card ending is said in pairs; the door code digit by digit.
SAY.insert(0, (r"\b(\d+)\.00\b", r"\1"))
SAY.insert(0, (r"\b4242\b", "forty-two forty-two"))
SAY.insert(0, (r"\b0000\b", "zero zero zero zero"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
WY = 2.15                                  # the wire, the machines and the router sit on this line
CL = np.array([-4.8, WY, 0])               # the card reader
SV = np.array([4.8, WY, 0])                # the server
MW, MH = 2.6, 1.2
WX = 3.5                                   # the wire runs between the machines' inner edges
RT_W, RT_H = 1.7, 0.8                      # the router in the middle
STUCK = np.array([0, 1.3, 0])              # the router's queue, just below it
MY = 0.15                                  # the kernel's notes under each machine
NW, NH = 3.5, 1.7
STRIP_Y = 0.15                             # the 17 bytes of the payment, in the centre
CELL = 0.32
ROW_Y = [-1.35, -1.85, -2.35]              # the log of the three messages
NAME_X, ARR_X0, ARR_X1, TXT_X = -5.85, -5.05, -4.45, -4.2
CAP_Y, BAR_Y = -3.15, -2.8

PAY = list("AUTH 4242 100.00") + ["\\n"]   # 17 bytes; the last is the newline that echo adds
A_ISN, B_ISN = 244700535, 4042781690


def n(x):
    return f"{x:,}"


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

    def steps(self, text, items, after=0.2):
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
        new = T(s, size, color).move_to([0, CAP_Y, 0])
        fit(new, 12.6)
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


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def swap(old, new, d=UP):
    """Replace one label with another: the old one leaves before the new one arrives, so they never overlap."""
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def baseline(t, s):
    """The y of a Text's baseline: the median bottom of its glyphs that have no descender."""
    chars = [c for c in s if not c.isspace()]
    ys = sorted(g.get_bottom()[1] for g, c in zip(t, chars) if c not in "gjpqy,;()Q\\")
    return ys[len(ys) // 2] if ys else t.get_bottom()[1]


def line_of(parts, size=20, gap=0.12):
    """One line of mixed text: parts are (text, color, mono). Pieces sit on one baseline."""
    g = VGroup()
    x = 0.0
    for s, color, mono in parts:
        t = (M if mono else T)(s, size, color)
        t.shift([x - t.get_left()[0], -baseline(t, s), 0])
        x = t.get_right()[0] + gap
        g.add(t)
    return g


# ---- the pieces ----
def machine(c, name, port, color):
    r = RoundedRectangle(corner_radius=0.14, width=MW, height=MH, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1).move_to(c)
    return VGroup(r, T(name, 26).move_to(c + [0, 0.2, 0])), M(port, 18, GREY_B).move_to(c + [0, -0.27, 0])


def router():
    r = RoundedRectangle(corner_radius=0.12, width=RT_W, height=RT_H, stroke_color=GREY_B, stroke_width=2.5).set_fill("#111111", 1)
    g = VGroup(r, T("router", 22, GREY_B)).move_to([0, WY, 0])
    g.set_z_index(5)
    return g


def wire():
    return VGroup(Line([-WX, WY, 0], [-RT_W / 2, WY, 0]), Line([RT_W / 2, WY, 0], [WX, WY, 0])).set_stroke(GREY_C, 3)


def parcel(lines, color, size=18):
    """A parcel on the wire: a small framed chip with one or two lines of monospace text."""
    if isinstance(lines, str):
        lines = [lines]
    t = VGroup(*[M(s, size, color) for s in lines]).arrange(DOWN, buff=0.1)
    r = RoundedRectangle(corner_radius=0.09, width=max(0.55, t.width + 0.36), height=t.height + 0.26, stroke_color=color,
                         stroke_width=2.5).set_fill(BLACK, 1)
    g = VGroup(r, t.move_to(r))
    g.set_z_index(3)
    return g


def blank(color, w=0.55):
    r = RoundedRectangle(corner_radius=0.08, width=w, height=0.36, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, 0.4), 1)
    flap = VMobject(stroke_color=color, stroke_width=2).set_points_as_corners([[-w / 2, 0.18, 0], [0, -0.02, 0], [w / 2, 0.18, 0]])
    g = VGroup(r, flap)
    g.set_z_index(3)
    return g


def send(p, right=True, rt=1.2, frac=1.0, keep=False, frm=None):
    """A parcel crossing the wire, from one machine to the other, passing behind the router (or starting at x=frm)."""
    w = p.width
    x0 = -WX + w / 2 + 0.12
    x1 = WX - w / 2 - 0.12
    a, b = (x0, x1) if right else (x1, x0)
    if frm is not None:
        a = frm
    b = a + frac * (b - a)
    p.move_to([a, WY, 0])
    seq = [FadeIn(p, run_time=0.15), MoveAlongPath(p, Line([a, WY, 0], [b, WY, 0]), rate_func=smooth, run_time=rt)]
    if not keep:
        seq.append(FadeOut(p, run_time=0.15))
    return Succession(*seq)


def notes(c, color):
    x0, x1 = c[0] - NW / 2, c[0] + NW / 2
    r = RoundedRectangle(corner_radius=0.14, width=NW, height=NH, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, 0.08), 1)
    r.move_to([c[0], MY, 0])
    return VGroup(r, left_at(T("kernel's notes", 18, GREY_B), x0 + 0.25, MY + 0.57),
                  left_at(T("mine", 20), x0 + 0.25, MY + 0.07), left_at(T("yours", 20), x0 + 0.25, MY - 0.45))


def note_num(c, k, s, color):
    x1 = c[0] + NW / 2
    return right_at(M(s, 20, color), x1 - 0.25, MY + (0.07 if k == 0 else -0.45))


def strip(first=None):
    """The 17 bytes of the payment as cells, each with its number underneath (the last three digits if first is set)."""
    g, nums = VGroup(), VGroup()
    x0 = -CELL * len(PAY) / 2
    for i, ch in enumerate(PAY):
        cx = x0 + (i + 0.5) * CELL
        cell = Square(CELL, stroke_color=BLUE_M, stroke_width=2).set_fill(fillc(BLUE_M, 0.2), 1).move_to([cx, STRIP_Y, 0])
        txt = M(ch, 16 if len(ch) > 1 else 20).move_to(cell) if ch != " " else VGroup()
        if ch == ".":
            txt.shift(0.08 * DOWN)                 # a full stop sits on the line, not in the middle
        g.add(VGroup(cell, txt))
        lab = str(i) if first is None else str(first + i)
        nums.add(M(lab, 13 if first else 15, GREY_B).move_to([cx, STRIP_Y - 0.37, 0]))
    return g, nums


def arrow_r(y, right=True, color=GREY_B):
    a, b = (ARR_X0, ARR_X1) if right else (ARR_X1, ARR_X0)
    return Arrow([a, y, 0], [b, y, 0], buff=0, stroke_width=3, color=color, max_tip_length_to_length_ratio=0.3)


def row(k, parts, size=22):
    return left_at(line_of(parts, size), TXT_X, ROW_Y[k])


class TcpHandshake(Base):
    """net-07, section 0. A card reader is about to send AUTH 4242 100.00. TCP numbers bytes and an ACK means "every
    byte before this one", so both sides must agree a start. Always 0 breaks: a stuck copy from the last connection on
    the same ports fits the new one. So each side picks a random start, and tells the other like a phone call on a
    bad line: three messages, the first ACK being the start plus one. The agreed numbers are the connection. Cost:
    one round trip; an ACK comes from the kernel, not the program. Check: the ACK for the 17 bytes."""

    def set_note(self, side, k, s, color):
        c = CL if side == 0 else SV
        new = note_num(c, k, s, color)
        old, self.nn[side][k] = self.nn[side][k], new
        return [swap(old, new)]

    def set_row(self, k, parts, size=22):
        new = row(k, parts, size)
        old, self.rows[k] = self.rows[k], new
        return [swap(old, new, RIGHT)]

    def roll(self, side, final, color):
        """The kernel picks its number: a few random draws, then the one it keeps."""
        rnd = random.Random(7 + side)
        out = []
        for _ in range(5):
            v = rnd.randrange(10 ** 8, 4 * 10 ** 9)
            out.append((lambda v=v: self.set_note(side, 0, n(v), GREY_B), 0.16))
        out.append((lambda: self.set_note(side, 0, n(final), color), 0.3))
        return out

    def construct(self):
        self.capm = None
        self.nn = [[None, None], [None, None]]
        self.rows = [None, None, None]
        self.title_card("What is a TCP connection?", "three messages and two random numbers")

        # ---------------- scene 1: the question ----------------
        cl, cl_port = machine(CL, "card reader", "port 50744", BLUE_M)
        sv, sv_port = machine(SV, "server", "port 9000", GOLD_M)
        wr, rt = wire(), router()
        req = VGroup(RoundedRectangle(corner_radius=0.1, width=3.2, height=0.52, stroke_color=BLUE_M, stroke_width=2.5).set_fill(BLACK, 1),
                     M("AUTH 4242 100.00", 22)).move_to([CL[0] + 0.3, 3.2, 0])
        req[1].move_to(req[0])
        self.steps("A card reader is about to send one short line to a server. It's a made-up request: approve 100.00 on the card ending 4242.", [
            (lambda: [FadeIn(cl), FadeIn(sv)], 0.8),
            (lambda: [Create(wr), FadeIn(rt)], 0.7),
            "It's a made-up",
            (lambda: [FadeIn(req, shift=0.15 * DOWN)], 0.7),
        ])
        big = M(n(A_ISN), 44, BLUE_M).move_to([0, 0.35, 0])
        self.steps("But before a single byte of it moves, the two machines trade three short messages, full of odd numbers like 244,700,535.", [
            "three short",
            (lambda: [send(blank(BLUE_M), True, 0.75)], 0.95),
            (lambda: [send(blank(GOLD_M), False, 0.75)], 0.95),
            (lambda: [send(blank(BLUE_M), True, 0.75)], 0.95),
            "odd numbers",
            (lambda: [FadeIn(big, scale=0.8)], 0.6),
        ])
        qm = T("?", 60, YELLOW_M).next_to(big, RIGHT, buff=0.35)
        up = Line([0, WY + RT_H / 2, 0], [0, 3.45, 0], stroke_color=GREY_D, stroke_width=3)

        def strangers():
            return [LaggedStart(*[travel(Line([0, 3.45, 0], [0, WY + RT_H / 2, 0]), GREY_B, 0.5) for _ in range(3)],
                                *[travel(Line([RT_W / 2, WY, 0], [WX, WY, 0]) if i % 2 else Line([-RT_W / 2, WY, 0], [-WX, WY, 0]), GREY_B, 0.6)
                                  for i in range(4)], lag_ratio=0.15)]
        self.steps("Why three? And what is a connection, anyway? There's no wire that belongs to just these two.", [
            (lambda: [FadeIn(qm, scale=0.6)], 0.5),
            "There's no wire",
            (lambda: [Create(up), *self.cap("the wires and routers carry everyone's parcels")], 0.6),
            (lambda: strangers(), 2.0),
        ])

        # ---------------- scene 2: the pieces we know ----------------
        self.steps("First, the pieces. Data travels in packets: small parcels of bytes, addressed to a machine, and to a port, "
                   "the number of one program on it. Here the reader uses port 50744, and the server port 9000.", [
            (lambda: [FadeOut(big), FadeOut(qm), *self.uncap()], 0.5),
            "in packets",
            (lambda: [send(blank(BLUE_M), True, 1.0)], 1.3),
            (lambda: self.cap("a packet: a small parcel of bytes, with an address on it"), 0.5),
            "Here the reader",
            (lambda: [FadeIn(cl_port, shift=0.1 * UP)], 0.6),
            "the server port",
            (lambda: [FadeIn(sv_port, shift=0.1 * UP)], 0.6),
        ])
        self.steps("On the way, routers pass the parcels along, for everyone.", [
            (lambda: [glow(rt[0], GREY_B, 1.05), *self.cap("a router: passes packets between networks"), *strangers()], 2.0),
        ])
        self.steps("In UDP and the sockets API, we numbered each message from 0, the other side answered with an ACK, got it, "
                   "and we resent anything unanswered.", [
            (lambda: [FadeOut(up), *self.cap("last time: number each message, ACK each one, resend what isn't ACKed")], 0.6),
            "we numbered",
            (lambda: [send(parcel("message 0", BLUE_M), True, 1.0)], 1.3),
            "with an ACK",
            (lambda: [send(parcel("ACK 0", GOLD_M), False, 1.0)], 1.3),
        ])
        cells, nums = strip()
        self.steps("TCP does that work for us. It's a set of rules followed by each machine's kernel, the core of its operating system. "
                   "And it numbers every byte, not every message.", [
            (lambda: self.cap("TCP: rules each machine's kernel follows (the kernel: the core of the operating system)"), 0.6),
            "it numbers every",
            (lambda: [ReplacementTransform(req, cells)], 1.0),
            (lambda: [LaggedStart(*[FadeIn(x, shift=0.1 * UP) for x in nums], lag_ratio=0.08)], 1.2),
        ])
        br = Brace(VGroup(*cells[:10]), UP, buff=0.08, color=GOLD_M)
        br_t = line_of([("ACK", GOLD_M, True), ("10:", GOLD_M, True), ("I have bytes 0 to 9", GOLD_M, False)], 20).next_to(br, UP, buff=0.12)
        self.steps("And its ACK means: I have every byte before this one. ACK 10 means bytes 0 to 9 are here.", [
            (lambda: self.cap("TCP's ACK: I have every byte before this one"), 0.5),
            "ACK 10",
            (lambda: [GrowFromCenter(br), FadeIn(br_t, shift=0.1 * DOWN)], 0.8),
            (lambda: [LaggedStart(*[x.animate(rate_func=there_and_back).set_color(GOLD_M) for x in nums[:10]], lag_ratio=0.1)], 1.2),
        ])
        q0 = T("?", 30, YELLOW_M).next_to(nums[0], LEFT, buff=0.3)
        self.steps("So before the first byte travels, both sides must agree where the numbering starts.", [
            (lambda: [FadeOut(br), FadeOut(br_t), *self.cap("where does the numbering start?", YELLOW_M)], 0.6),
            "where the numbering",
            (lambda: [Indicate(nums[0], color=YELLOW_M, scale_factor=1.8), FadeIn(q0)], 0.9),
        ])

        # ---------------- scene 3: the obvious fix, broken ----------------
        took_c = np.array([SV[0], MY, 0])
        took = VGroup(RoundedRectangle(corner_radius=0.14, width=NW, height=NH, stroke_color=GOLD_M, stroke_width=2.5).set_fill(fillc(GOLD_M, 0.08), 1).move_to(took_c),
                      left_at(T("the server took", 18, GREY_B), SV[0] - NW / 2 + 0.25, MY + 0.57))
        t1 = left_at(M("bytes 0 to 16", 20), SV[0] - NW / 2 + 0.25, MY + 0.07)
        t2 = left_at(M("bytes 0 to 16", 20, RED_M), SV[0] - NW / 2 + 0.25, MY - 0.45)
        ok1 = tick(True, 0.13).move_to([SV[0] + NW / 2 - 0.3, MY + 0.07, 0])
        self.steps("The obvious answer: always start at 0. And to be fair, it works. The reader sends the payment, bytes 0 to 16, "
                   "the server takes it, and the connection closes.", [
            (lambda: [FadeOut(q0), *self.cap("the obvious answer: always start at 0")], 0.6),
            "The reader sends",
            (lambda: [send(parcel("bytes 0 to 16", BLUE_M), True, 1.3)], 1.6),
            "the server takes",
            (lambda: [FadeIn(took), FadeIn(t1, shift=0.1 * RIGHT), Create(ok1)], 0.7),
            "the connection closes",
            (lambda: self.cap("connection 1: done, and closed"), 0.5),
        ])
        stuck = parcel("bytes 0 to 16", GREY_B).move_to(STUCK)
        stuck_l = left_at(T("stuck in a queue", 18, GREY_B), STUCK[0] + stuck.width / 2 + 0.2, STUCK[1])
        self.steps("But a copy of that parcel got stuck for a while in a router's queue.", [
            "a copy",
            (lambda: [FadeIn(stuck, shift=0.6 * DOWN), glow(rt[0], GREY_B, 1.05)], 0.8),
            (lambda: [FadeIn(stuck_l)], 0.4),
        ])
        self.steps("A second later, the reader opens a new connection, on the same two ports, and starts at 0 again.", [
            (lambda: [glow(cl[0], BLUE_M, 1.04), *self.cap("connection 2: the same two ports, and it starts at 0 again", WHITE)], 0.8),
            "starts at 0",
            (lambda: [Indicate(nums[0], color=YELLOW_M, scale_factor=1.8)], 0.8),
        ])
        two = T("two payments", 22, RED_M).move_to([SV[0], MY - 1.1, 0])
        no2 = tick(True, 0.13).move_to([SV[0] + NW / 2 - 0.3, MY - 0.45, 0]).set_stroke(RED_M)
        self.steps("Now the stuck copy turns up. It fits the new connection perfectly, so the server takes it. "
                   "One tap of a card, two payments.", [
            (lambda: [FadeOut(stuck_l), stuck.animate.move_to([0, WY, 0]).set_opacity(0)], 0.5),
            (lambda: [send(parcel("bytes 0 to 16", RED_M), True, 0.9, frm=0)], 1.1),
            "so the server",
            (lambda: [FadeIn(t2, shift=0.1 * RIGHT), Create(no2)], 0.6),
            "two payments",
            (lambda: [FadeIn(two, shift=0.1 * UP), glow(took[0], RED_M, 1.03)], 0.8),
        ])
        self.steps("Well... the customer will have questions. What we want are numbers an old connection would never have used.", [
            "What we want",
            (lambda: self.cap("wanted: numbers an old connection never used", YELLOW_M), 0.6),
        ])

        # ---------------- scene 4: a random start ----------------
        nc, ns = notes(CL, BLUE_M), notes(SV, GOLD_M)
        self.steps("So each side picks its own starting number, a new one for every connection.", [
            (lambda: [FadeOut(VGroup(took, t1, t2, ok1, no2, two)), FadeOut(cells), FadeOut(nums), *self.uncap()], 0.6),
            (lambda: [FadeIn(nc, shift=0.1 * DOWN), FadeIn(ns, shift=0.1 * DOWN)], 0.6),
            *self.roll(0, A_ISN, BLUE_M),
            *self.roll(1, B_ISN, GOLD_M),
        ])
        self.steps("Starting at 0 every time is like a door code of 0000. It's the first thing anyone would try.", [
            (lambda: self.cap("starting at 0 every time: a door code of 0000"), 0.6),
        ], after=0.5)
        self.steps("TCP's rules mix a fast clock with the ports and a secret, so every connection starts somewhere different, "
                   "and an outsider can't guess where. Guess the numbers, and you could slip your own bytes into somebody else's connection.", [
            (lambda: self.cap("a clock that ticks every 4 microseconds, scrambled with the addresses, the ports and a secret"), 0.5),
            "the ports",
            (lambda: [Indicate(cl_port, color=BLUE_M), Indicate(sv_port, color=GOLD_M)], 0.8),
            "so every connection",
            (lambda: [glow(nc[0], BLUE_M, 1.03), glow(ns[0], GOLD_M, 1.03)], 0.8),
            "Guess the numbers",
            (lambda: self.cap("guess the numbers, and you can slip bytes into someone else's connection", RED_M), 0.5),
        ])

        # ---------------- scene 5: the phone call ----------------
        self.steps("Now each side must tell the other its number, and know that it arrived. "
                   "You've had this problem on a phone call with a bad line.", [
            (lambda: [*self.uncap(), *self.set_note(0, 1, "?", YELLOW_M), *self.set_note(1, 1, "?", YELLOW_M)], 0.6),
            (lambda: self.cap("tell your number, and know it arrived"), 0.5),
            "You've had",
            (lambda: self.cap("a phone call on a bad line", WHITE), 0.5),
        ], after=0.4)
        arrs = [arrow_r(ROW_Y[0], True, BLUE_M), arrow_r(ROW_Y[1], False, GOLD_M), arrow_r(ROW_Y[2], True, BLUE_M)]
        ph = [[("can you hear me?", WHITE, False)],
              [("yes, I hear you.", GOLD_M, False), ("can you hear me?", WHITE, False)],
              [("yes.", GOLD_M, False)]]
        self.steps("One person says: can you hear me? The other says: yes, I hear you. Can you hear me? And the first says: yes.", [
            (lambda: [send(parcel("hear me?", BLUE_M, 20), True, 0.9), GrowArrow(arrs[0]), *self.set_row(0, ph[0])], 1.2),
            "The other says",
            (lambda: [send(parcel("yes. hear me?", GOLD_M, 20), False, 1.0), GrowArrow(arrs[1]), *self.set_row(1, ph[1])], 1.3),
            "And the first",
            (lambda: [send(parcel("yes", BLUE_M, 20), True, 0.8), GrowArrow(arrs[2]), *self.set_row(2, ph[2])], 1.1),
        ])
        self.steps("Each person needs to know their own voice gets through, so each one asks, and each one answers. "
                   "That's four lines, but the middle two fit in one breath, so it takes three.", [
            "so each one asks",
            (lambda: [Indicate(self.rows[0], color=BLUE_M, scale_factor=1.05)], 0.6),
            (lambda: [Indicate(self.rows[1][1], color=GOLD_M, scale_factor=1.08)], 0.6),
            "each one answers",
            (lambda: [Indicate(self.rows[1][0], color=GOLD_M, scale_factor=1.08)], 0.6),
            (lambda: [Indicate(self.rows[2], color=BLUE_M, scale_factor=1.1)], 0.6),
            "the middle two",
            (lambda: [*self.cap("two questions and two answers; the middle two share one message")], 0.6),
        ])
        self.steps("TCP works the same way. Can you hear me is: here's my starting number. Yes, I hear you, is an ACK. "
                   "And the middle message carries both.", [
            "Can you hear me",
            (lambda: self.cap("can you hear me?  =  here's my starting number", WHITE), 0.5),
            "Yes, I hear you",
            (lambda: self.cap("yes, I hear you  =  an ACK", WHITE), 0.5),
            "And the middle",
            (lambda: [*self.cap("the middle message: an ACK and a starting number"), glow_row(self.rows[1])], 0.8),
        ])

        # ---------------- scene 6: three messages, with numbers ----------------
        r0 = [("my bytes start after", WHITE, False), (n(A_ISN), BLUE_M, True)]
        self.steps("First message. The reader says: my bytes start after 244,700,535.", [
            (lambda: [*self.uncap(), *self.set_row(0, r0)], 0.7),
            (lambda: [send(parcel(n(A_ISN), BLUE_M), True, 1.1)], 1.3),
            (lambda: self.set_note(1, 1, n(A_ISN), BLUE_M), 0.4),
        ])
        r1q = [("next I expect", WHITE, False), ("?", YELLOW_M, True)]
        self.steps("The server answers: the next byte I expect from you is... The reader's number ends in 535. Pause and guess.", [
            (lambda: self.set_row(1, r1q), 0.7),
            "ends in 535",
            (lambda: [Indicate(self.nn[0][0], color=BLUE_M, scale_factor=1.12)], 0.8),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        r1a = [("next I expect", WHITE, False), (n(A_ISN + 1), BLUE_M, True)]
        plus = T("start + 1", 20, YELLOW_M)
        self.steps("536. One more. This first message carries no data, yet it uses up one number, so the answer is the start plus one.", [
            (lambda: [*self.uncap(), *self.set_row(1, r1a)], 0.6),
            "One more",
            (lambda: [FadeIn(plus.next_to(self.rows[1], RIGHT, buff=0.35), shift=0.1 * LEFT)], 0.5),
            "carries no data",
            (lambda: self.cap("the first message carries no data, but it uses up one number"), 0.5),
        ])
        r1 = [("next I expect", WHITE, False), (n(A_ISN + 1) + ",", BLUE_M, True), ("and mine start after", WHITE, False), (n(B_ISN), GOLD_M, True)]
        self.steps("In the same message, the server adds its own starting number.", [
            (lambda: [FadeOut(plus), *self.uncap(), *self.set_row(1, r1)], 0.6),
            (lambda: [send(parcel([f"expect {n(A_ISN + 1)}", f"start {n(B_ISN)}"], GOLD_M, 16), False, 1.0)], 1.3),
            (lambda: self.set_note(0, 1, n(B_ISN), GOLD_M), 0.4),
        ])
        r2 = [("next I expect", WHITE, False), (n(B_ISN + 1), GOLD_M, True)]
        oks = [tick(True, 0.14).move_to([CL[0] + NW / 2 - 0.3, MY + 0.57, 0]), tick(True, 0.14).move_to([SV[0] + NW / 2 - 0.3, MY + 0.57, 0])]
        self.steps("Third message. The reader answers: the next byte I expect from you is the one ending in 691. "
                   "Now both sides know both numbers, and the payment can go.", [
            (lambda: self.set_row(2, r2), 0.7),
            "ending in 691",
            (lambda: [send(parcel(f"expect {n(B_ISN + 1)}", BLUE_M, 16), True, 1.1)], 1.3),
            "Now both sides",
            (lambda: [Create(oks[0]), Create(oks[1])], 0.6),
        ])

        # ---------------- scene 7: the names ----------------
        names = [M("SYN", 20, TEAL_M), M("SYN-ACK", 20, TEAL_M), M("ACK", 20, TEAL_M)]
        for k, m in enumerate(names):
            m.move_to([NAME_X, ROW_Y[k], 0])
        self.steps("This exchange is the three-way handshake. Each message is named after its flag, a marker at the front: "
                   "SYN, short for synchronize, then SYN-ACK, then ACK.", [
            (lambda: [FadeOut(VGroup(*oks)), *self.cap("the three-way handshake", TEAL_M, 28)], 0.6),
            "SYN, short",
            (lambda: [FadeIn(names[0], shift=0.1 * RIGHT)], 0.5),
            "then SYN-ACK",
            (lambda: [FadeIn(names[1], shift=0.1 * RIGHT)], 0.5),
            "then ACK",
            (lambda: [FadeIn(names[2], shift=0.1 * RIGHT)], 0.5),
        ])
        conn = T("the connection", 30, TEAL_M).move_to([0, MY + 0.1, 0])
        c_arrs = [Arrow(conn.get_left() + 0.1 * LEFT, [CL[0] + NW / 2 + 0.08, MY + 0.1, 0], buff=0, stroke_width=3, color=TEAL_M,
                        max_tip_length_to_length_ratio=0.25),
                  Arrow(conn.get_right() + 0.1 * RIGHT, [SV[0] - NW / 2 - 0.08, MY + 0.1, 0], buff=0, stroke_width=3, color=TEAL_M,
                        max_tip_length_to_length_ratio=0.25)]
        self.steps("The starting numbers are called initial sequence numbers. And the connection? It's these numbers, kept in both kernels. "
                   "No wire belongs to these two.", [
            (lambda: [*self.cap("initial sequence numbers: the two starting numbers", WHITE),
                      Indicate(self.nn[0][0], color=BLUE_M, scale_factor=1.12), Indicate(self.nn[1][0], color=GOLD_M, scale_factor=1.12)], 0.9),
            "And the connection",
            (lambda: [FadeIn(conn, scale=0.9)], 0.6),
            "It's these numbers",
            (lambda: [GrowArrow(c_arrs[0]), GrowArrow(c_arrs[1]), glow(nc[0], TEAL_M, 1.03), glow(ns[0], TEAL_M, 1.03)], 0.9),
            "No wire",
            (lambda: [glow(wr, GREY_B, 1.0)], 0.8),
        ])

        # ---------------- scene 8: where the phone picture breaks ----------------
        self.steps("The phone picture breaks in one place: a word never turns up a minute late. A packet can.", [
            (lambda: self.cap("where the phone picture breaks"), 0.5),
            "a word never",
            (lambda: self.cap("a word never turns up a minute late. a packet can."), 0.5),
        ])
        old = parcel("old numbers", RED_M).move_to(STUCK)
        oldp = parcel("old numbers", RED_M)
        drop_x = tick(False, 0.17)
        drop_t = T("doesn't fit: dropped", 20, RED_M)
        self.steps("Remember the stuck copy? It carries the old connection's numbers, nowhere near this one's. "
                   "It doesn't fit, so the server throws it away.", [
            (lambda: [FadeOut(conn), FadeOut(c_arrs[0]), FadeOut(c_arrs[1]), *self.uncap(), FadeIn(old, shift=0.4 * DOWN)], 0.7),
            "nowhere near",
            (lambda: [Indicate(old, color=RED_M, scale_factor=1.1)], 0.6),
            "It doesn't fit",
            (lambda: [old.animate.move_to([0, WY, 0]).set_opacity(0)], 0.4),
            (lambda: [send(oldp, True, 0.9, keep=True, frm=0)], 1.05),
            (lambda: [Create(drop_x.move_to([WX - 0.35, WY + 0.55, 0])),
                      FadeIn(drop_t.move_to([0, MY + 0.1, 0]))], 0.5),
        ])

        # ---------------- scene 9: the cost, and what an ACK isn't ----------------
        rtl = T("one round trip", 22, GREY_B).move_to([0, WY + 0.75, 0])
        self.steps("All this costs one round trip, there and back, before the payment moves. On the lab network, that's a tenth of a millisecond.", [
            (lambda: [FadeOut(drop_x), FadeOut(drop_t), FadeOut(oldp)], 0.4),
            "one round trip",
            (lambda: [Succession(travel(Line([-WX, WY, 0], [WX, WY, 0]), YELLOW_M, 0.9), travel(Line([WX, WY, 0], [-WX, WY, 0]), YELLOW_M, 0.9)),
                      FadeIn(rtl)], 2.1),
            "On the lab",
            (lambda: self.cap("on the lab network: a tenth of a millisecond"), 0.5),
        ])
        self.steps("To a bank 70 milliseconds away, that's 70 milliseconds of small talk before every new connection. "
                   "So keep connections open, and reuse them.", [
            (lambda: self.cap("to a bank 70 milliseconds away: 70 milliseconds before every new connection", WHITE), 0.6),
            "of small talk",
            (lambda: [glow_row(VGroup(*self.rows))], 0.9),
            "So keep",
            (lambda: [FadeOut(rtl), *self.cap("keep connections open, and reuse them", GREEN_M, 28)], 0.6),
        ])

        # ---------------- scene 10: the moral, and a check ----------------
        self.steps("So, what is a connection? Two random starting numbers, swapped in three messages, and kept by both sides.", [
            (lambda: self.cap("what is a connection?", WHITE), 0.5),
            "Two random",
            (lambda: [Indicate(self.nn[0][0], color=BLUE_M, scale_factor=1.12), Indicate(self.nn[1][0], color=GOLD_M, scale_factor=1.12)], 0.8),
            "swapped in three",
            (lambda: [LaggedStart(*[Indicate(r, color=TEAL_M, scale_factor=1.04) for r in self.rows], lag_ratio=0.3)], 1.2),
            "kept by both",
            (lambda: [glow(nc[0], BLUE_M, 1.03), glow(ns[0], GOLD_M, 1.03)], 0.8),
        ])
        cells2, nums2 = strip(536)
        b17 = Brace(cells2, DOWN, buff=0.42, color=GREY_B)
        b17t = T("17 bytes", 18, GREY_B).next_to(b17, DOWN, buff=0.08)
        ackq = line_of([("ACK", GOLD_M, True), ("?", YELLOW_M, True)], 24).move_to([0, STRIP_Y + 0.62, 0])
        self.steps("One quick check. The payment is 17 bytes, starting at byte 536. "
                   "What number does the server's ACK carry? Pause and think.", [
            (lambda: [*self.uncap(), FadeIn(cells2), FadeIn(nums2[0]), FadeIn(b17), FadeIn(b17t)], 0.7),
            "starting at",
            (lambda: [Indicate(nums2[0], color=BLUE_M, scale_factor=1.6)], 0.8),
            "What number",
            (lambda: [FadeIn(ackq, shift=0.1 * DOWN)], 0.5),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        acka = line_of([("ACK", GOLD_M, True), ("553:", GOLD_M, True), ("the next byte I expect", GOLD_M, False)], 22).move_to(ackq)
        self.steps("553. The bytes are 536 to 552, and the ACK names the next one it expects.", [
            (lambda: [*self.uncap(), send(parcel("17 bytes", BLUE_M, 16), True, 0.9)], 1.2),
            (lambda: [swap(ackq, acka), send(parcel("ACK 244,700,553", GOLD_M, 16), False, 0.9)], 1.2),
            "552",
            (lambda: [FadeIn(nums2[-1], scale=1.6)], 0.6),
        ], after=0.2)
        self.play(*self.cap("a connection: two numbers, three messages, kept by both sides", WHITE, 26), run_time=0.7)
        self.wait(2.0)


def glow_row(m):
    return Indicate(m, color=TEAL_M, scale_factor=1.03)
