from sfz import *

SAY.insert(0, (r"\bexample\.com\b", "example dot com"))
SAY.insert(0, (r"\b0x0800\b", "hex zero eight zero zero"))
SAY.insert(0, (r"\bMAC\b", "mac"))
SAY.insert(0, (r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b", r"\1 dot \2 dot \3 dot \4"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
MY0, MY = 0.35, 2.85                     # the machine row: in the opening, then at the top
LAP_X, SRV_X = -5.25, 5.25
MW, MH = 2.3, 0.95
RW = 1.8                                 # a router's width
EX0, EX1, EY0, EY1 = -4.2, 3.55, -2.3, 1.5   # the outermost wrapper (Ethernet)
BAND, PAD = 0.6, 0.17
NOUN_X = -4.45                           # the analogy's nouns, right-aligned
CNT_X, CNT_Y = 5.3, -0.2                 # the running size
MARK_X = 3.9
CAP_Y, BAR_Y = -2.95, -3.42
COL = {0: WHITE, 1: BLUE_M, 2: GREEN_M, 3: GOLD_M}
REQ = ["GET / HTTP/1.1", "Host: example.com", "User-Agent: curl/8.5.0", "Accept: */*"]


def R(k):
    """Bounds of wrapper k: 0 the letter (HTTP), 1 TCP's envelope, 2 IP's parcel, 3 Ethernet's label."""
    d = 3 - k
    return EX0 + d * PAD, EX1 - d * PAD, EY0 + d * PAD, EY1 - d * BAND


def band_y(k):
    x0, x1, y0, y1 = R(k)
    return (y0 + y1) / 2 if k == 0 else y1 - BAND / 2


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


def glow(m, color=YELLOW_M, s=1.02):
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


def token(color=GOLD_M):
    return RoundedRectangle(corner_radius=0.07, width=0.55, height=0.3, stroke_color=color, stroke_width=2.5).set_fill(
        fillc(color, 0.6), 1).set_z_index(3)


def ride(x0, x1, y=MY, color=GOLD_M):
    """The frame, a small chip, crossing one link."""
    c = token(color).move_to([x0, y, 0])
    return Succession(FadeIn(c, run_time=0.1), MoveAlongPath(c, Line([x0, y, 0], [x1, y, 0]), rate_func=smooth, run_time=1.0),
                      FadeOut(c, run_time=0.15))


def peel(g):
    """A wrapper comes off: it lifts and fades."""
    return g.animate.shift(0.45 * UP).set_opacity(0)


# ---- the pieces ----
def machine(name, sub, x, y, color=WHITE, w=MW, mono=True):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=MH, stroke_color=color, stroke_width=3).set_fill(BLACK, 1)
    r.move_to([x, y, 0])
    s = (M(sub, 15, GREY_B) if mono else T(sub, 17, GREY_B)).move_to([x, y - 0.2, 0])
    return VGroup(r, T(name, 22).move_to([x, y + 0.17, 0]), s).set_z_index(1)


def wrap_rect(k):
    x0, x1, y0, y1 = R(k)
    fill = "#121212" if k == 0 else fillc(COL[k])
    r = RoundedRectangle(corner_radius=0.12, width=x1 - x0, height=y1 - y0, stroke_color=COL[k], stroke_width=3)
    return r.set_fill(fill, 1).move_to([(x0 + x1) / 2, (y0 + y1) / 2, 0]).set_z_index(-1 - k)


def noun(k, s):
    return right_at(T(s, 20, GREY_B), NOUN_X, band_y(k)).set_z_index(2)


def afield(k, s):
    """The analogy's word on a band (serif), where the technical address will go."""
    x0 = R(k)[0]
    return left_at(T(s, 21, COL[k]), x0 + 2.8, band_y(k)).set_z_index(2)


def tname(k, name, n):
    x0 = R(k)[0]
    g = VGroup(T(name, 22, COL[k]), M(f"{n} bytes", 14, GREY_B)).arrange(RIGHT, buff=0.15)
    return left_at(g, x0 + 0.25, band_y(k)).set_z_index(2)


def tfield(k, s, color=WHITE, mono=True):
    x0 = R(k)[0]
    return left_at((M(s, 17, color) if mono else T(s, 20, color)), x0 + 2.8, band_y(k)).set_z_index(2)


def xfield(k, s, color):
    x1 = R(k)[1]
    return right_at(M(s, 17, color), x1 - 0.25, band_y(k)).set_z_index(2)


def mark(ok, k):
    at = [MARK_X, band_y(k), 0]
    if ok is None:
        return T("?", 30, YELLOW_M).move_to(at)
    if ok == "new":
        return T("new", 20, YELLOW_M).move_to([MARK_X + 0.08, band_y(k), 0])
    return tick(ok, 0.14).move_to(at)


class NetEncapsulation(Base):
    """net-01, section 1. One long wire? No: curl's 74 bytes get a TCP envelope (port), an IP parcel (street address) and
    an Ethernet courier label (the next card), 140 bytes in all. A router, the depot, swaps only the label and lowers the
    TTL; the server unwraps by following each header's "what's inside" field: 0x0800, protocol 6, port 80."""

    def set_count(self, n, unit):
        new = VGroup(M(f"{n} bytes", 28).move_to([CNT_X, CNT_Y, 0]), T(unit, 20, GREY_B).move_to([CNT_X, CNT_Y - 0.5, 0]))
        old, self.cnt = self.cnt, new
        return [swap(old, new)]

    def set_field(self, attr, new):
        old = getattr(self, attr)
        setattr(self, attr, new)
        return [swap(old, new)]

    def construct(self):
        self.capm = self.cnt = None
        self.title_card("Envelopes inside envelopes", "how one request is wrapped, passed on and unwrapped")

        # ---------------- scene 1: one long wire? ----------------
        lap = machine("your laptop", "172.20.0.2", LAP_X, MY0)
        srv = machine("server", "104.20.23.154", SRV_X, MY0)
        wire = Line([LAP_X + MW / 2, MY0, 0], [SRV_X - MW / 2, MY0, 0], stroke_width=3, color=GREY_B).set_z_index(-8)
        self.steps("Picture yourself at a café with a laptop. You type the address of a web page, press Enter, "
                   "and the page appears in about a twentieth of a second.", [
            (lambda: [FadeIn(lap, shift=0.2 * UP)], 0.8),
            "the page appears",
            (lambda: [FadeIn(srv, shift=0.2 * UP)], 0.8),
        ])
        self.steps("It's easy to picture one long wire from your laptop to the computer that sent it, "
                   "with your request rushing along it in one piece.", [
            "one long wire",
            (lambda: [Create(wire)], 0.8),
            "rushing along",
            (lambda: [ride(LAP_X + MW / 2, SRV_X - MW / 2, MY0, WHITE)], 1.3),
        ])
        qm = T("?", 56, YELLOW_M).move_to([0, MY0 + 0.8, 0])
        self.steps("But that computer is many links away, behind machines owned by strangers. So how does a stranger's machine "
                   "know where to pass your request? And when it arrives, how does the far computer know which program it's for? "
                   "Hold those two questions.", [
            "many links away",
            (lambda: [wire.animate.set_stroke(opacity=0.35), FadeIn(qm, scale=0.6)], 0.7),
            "So how does",
            (lambda: self.cap("1. where should a machine on the way pass it?", WHITE), 0.5),
            "And when it arrives",
            (lambda: self.cap("1. where should a machine on the way pass it?      2. which program is it for?", WHITE), 0.5),
        ])

        # ---------------- scene 2: the request, and what it's missing ----------------
        big = VGroup(*[M(s, 26) for s in REQ]).arrange(DOWN, aligned_edge=LEFT, buff=0.18).move_to([0, -0.15, 0])
        big_n = M("74 bytes", 20, GREY_B).next_to(big, DOWN, buff=0.3)
        up = (MY - MY0) * UP
        self.steps("Let's look at the request. Ask curl, a program that fetches web pages from the command line, for example.com, "
                   "and it writes these 74 bytes of HTTP, the language that browsers and web servers speak.", [
            (lambda: [*self.uncap(), FadeOut(qm), VGroup(lap, srv).animate.shift(up), wire.animate.shift(up).set_stroke(opacity=1)], 1.0),
            "and it writes",
            (lambda: [FadeIn(big, shift=0.1 * UP), FadeIn(big_n)], 0.8),
            "HTTP, the language",
            (lambda: [Indicate(big[0], color=WHITE, scale_factor=1.06)], 0.8),
        ])
        slots = VGroup()
        for s, x in [("computer: ?", -3.4), ("program: ?", 0.0), ("next card: ?", 3.4)]:
            r = DashedVMobject(RoundedRectangle(corner_radius=0.1, width=2.7, height=0.55, stroke_color=GREY_B, stroke_width=2),
                               num_dashes=36).move_to([x, -2.2, 0])
            slots.add(VGroup(r, T(s, 20, GREY_B).move_to([x, -2.2, 0])))
        self.steps("Now notice what's missing. There's a site name, but no number for the computer, no number for the program, "
                   "and nothing the card next door could use.", [
            "a site name",
            (lambda: [Indicate(big[1], color=YELLOW_M, scale_factor=1.06)], 0.7),
            "no number for the computer",
            (lambda: [FadeIn(slots[0], shift=0.1 * UP)], 0.4),
            "no number for the program",
            (lambda: [FadeIn(slots[1], shift=0.1 * UP)], 0.4),
            "nothing the card",
            (lambda: [FadeIn(slots[2], shift=0.1 * UP)], 0.4),
        ])
        self.steps("curl hands these bytes to the kernel, the core of the operating system. "
                   "On the way down, the kernel has to add every address.", [
            "the kernel",
            (lambda: self.cap("the kernel: the core of the operating system"), 0.5),
            "add every address",
            (lambda: [LaggedStart(*[glow(s[0], YELLOW_M, 1.04) for s in slots], lag_ratio=0.3)], 1.1),
        ])
        self.steps("What we want: every machine on the way should find the one address it needs, "
                   "without reading your letter.", [
            "every machine",
            (lambda: self.cap("the wish: each machine finds the one address it needs, and reads nothing else", WHITE), 0.5),
        ])

        # ---------------- scene 3: posting a letter ----------------
        rects = {k: wrap_rect(k) for k in range(4)}
        small = VGroup(*[M(s, 16) for s in REQ]).arrange(DOWN, aligned_edge=LEFT, buff=0.09)
        left_at(small, R(0)[0] + 0.25, band_y(0)).set_z_index(2)
        nouns = {0: noun(0, "letter"), 1: noun(1, "envelope"), 2: noun(2, "parcel"), 3: noun(3, "courier label")}
        self.steps("Think of posting a letter. You write the letter.", [
            (lambda: [*self.uncap(), FadeOut(slots), FadeOut(big_n)], 0.5),
            "You write",
            (lambda: [ReplacementTransform(big, small), FadeIn(rects[0]), FadeIn(nouns[0])], 1.0),
        ])
        af = {1: afield(1, "flat 80"), 2: afield(2, "street address"), 3: afield(3, "next depot")}
        self.steps("It goes in an envelope with a flat number on it.", [
            "an envelope",
            (lambda: [FadeIn(rects[1], scale=1.05), FadeIn(nouns[1])], 0.7),
            "a flat number",
            (lambda: [FadeIn(af[1], shift=0.1 * DOWN)], 0.5),
        ])
        self.steps("That envelope goes inside a parcel with the street address.", [
            "inside a parcel",
            (lambda: [FadeIn(rects[2], scale=1.05), FadeIn(nouns[2])], 0.7),
            "the street address",
            (lambda: [FadeIn(af[2], shift=0.1 * DOWN)], 0.5),
        ])
        self.steps("Then a courier sticks a label on the outside. It says only which depot to drive to next.", [
            "sticks a label",
            (lambda: [FadeIn(rects[3], scale=1.05), FadeIn(nouns[3])], 0.7),
            "which depot",
            (lambda: [FadeIn(af[3], shift=0.1 * DOWN)], 0.5),
        ])
        self.steps("Each wrapper treats what's inside as sealed.", [
            (lambda: [LaggedStart(*[glow(rects[k], COL[k], 1.01) for k in (3, 2, 1)], lag_ratio=0.45)], 1.8),
        ])

        # ---------------- scene 4: the same picture in your laptop ----------------
        http_l = VGroup(T("HTTP request", 20), M("74 bytes", 15, GREY_B)).arrange(DOWN, buff=0.14, aligned_edge=RIGHT)
        right_at(http_l, R(0)[1] - 0.25, band_y(0)).set_z_index(2)
        self.steps("Now the same picture in your laptop. The letter is curl's request: 74 bytes of HTTP.", [
            "The letter is",
            (lambda: [FadeIn(http_l, shift=0.1 * LEFT), *self.set_count(74, "a message")], 0.7),
        ])
        self.steps("Each layer puts a header in front: a few bytes with its own addresses.", [
            (lambda: self.cap("a header: a few bytes in front, with that layer's addresses"), 0.5),
        ])
        tn = {1: tname(1, "TCP", 32), 2: tname(2, "IP", 20), 3: tname(3, "Ethernet", 14)}
        self.to = {1: tfield(1, "to port 80"), 2: tfield(2, "to 104.20.23.154"), 3: tfield(3, "to 22:d2:d5:a2:32:a3")}
        self.ttl = xfield(2, "TTL 64", GREEN_M)
        self.steps("The envelope is TCP's header, from the layer that picks the program and keeps the bytes in order. "
                   "32 bytes, with the two ports. 74 bytes become 106.", [
            (lambda: [*self.uncap(), glow(rects[1], BLUE_M, 1.01)], 0.6),
            "TCP's header",
            (lambda: [FadeIn(tn[1], shift=0.1 * RIGHT)], 0.5),
            "the two port",
            (lambda: [swap(af[1], self.to[1])], 0.6),
            "74 bytes become",
            (lambda: self.set_count(106, "a segment"), 0.6),
        ])
        self.steps("The parcel is IP's header: 20 bytes, with the two computers' IP addresses "
                   "and a counter called the time to live. 126 bytes.", [
            (lambda: [glow(rects[2], GREEN_M, 1.01)], 0.6),
            "IP's header",
            (lambda: [FadeIn(tn[2], shift=0.1 * RIGHT)], 0.5),
            "the two computers",
            (lambda: [swap(af[2], self.to[2])], 0.6),
            "a counter",
            (lambda: [FadeIn(self.ttl, shift=0.1 * LEFT)], 0.5),
            "126 bytes",
            (lambda: self.set_count(126, "a packet"), 0.6),
        ])
        self.steps("The courier label is Ethernet's header: 14 bytes, with two MAC addresses, the names of network cards "
                   "on this one link. 140 bytes, sent as one frame.", [
            (lambda: [glow(rects[3], GOLD_M, 1.01)], 0.6),
            "Ethernet's header",
            (lambda: [FadeIn(tn[3], shift=0.1 * RIGHT)], 0.5),
            "two MAC",
            (lambda: [swap(af[3], self.to[3])], 0.6),
            "140 bytes",
            (lambda: self.set_count(140, "a frame"), 0.6),
        ])
        self.steps("This wrapping is called encapsulation. Each layer wraps what it was handed, and never looks inside.", [
            "encapsulation",
            (lambda: self.cap("encapsulation: each layer wraps what it was handed", WHITE), 0.6),
        ])
        self.steps("That's 66 bytes of wrapping around 74 bytes of letter. Online shops would be proud. "
                   "But every wrapper earns its place, as we're about to see.", [
            (lambda: [*self.cap("32 + 20 + 14 = 66 bytes of wrapping, around 74 bytes of letter"),
                      LaggedStart(*[Indicate(tn[k][1], color=YELLOW_M) for k in (1, 2, 3)], lag_ratio=0.3)], 1.2),
            "Online shops",
            (lambda: [Indicate(http_l[1], color=WHITE)], 0.8),
        ])

        # ---------------- scene 5: the depot ----------------
        rt = machine("router", "the depot", 0, MY, GREY_B, w=RW, mono=False)
        mac_lap = M("b6:99:4a:b0:80:7f", 15, GREY_B).move_to([LAP_X, MY - 0.72, 0])
        mac_rt = M("22:d2:d5:a2:32:a3", 15, YELLOW_M).move_to([0, MY - 0.72, 0])
        L1 = (LAP_X + MW / 2 + 0.05, -RW / 2 - 0.05)
        L2 = (RW / 2 + 0.05, SRV_X - MW / 2 - 0.05)
        self.steps("Back to the long wire. It isn't one wire. Your laptop's card can only reach the cards on its own link, "
                   "so the label names the next card: the router's.", [
            (lambda: self.uncap(), 0.4),
            "It isn't one wire",
            (lambda: [FadeIn(rt, shift=0.3 * DOWN)], 0.8),
            "Your laptop's card",
            (lambda: [FadeIn(mac_lap)], 0.5),
            "the label names",
            (lambda: [FadeIn(mac_rt), Indicate(self.to[3], color=YELLOW_M, scale_factor=1.05)], 0.9),
        ])
        self.steps("A router is a machine on two links that passes packets from one to the next, like a courier's depot.", [
            (lambda: self.cap("a router: a machine on two links that passes packets from one to the next"), 0.5),
            "from one to",
            (lambda: [ride(*L1)], 1.1),
            (lambda: [glow(rt[0], GREY_B, 1.04)], 0.5),
        ])
        qs = [mark(None, k) for k in (3, 2, 1, 0)]
        self.steps("When the frame leaves the depot for the next link, which labels will have changed? Pause and guess.", [
            (lambda: self.uncap(), 0.3),
            "which labels",
            (lambda: [LaggedStart(*[FadeIn(q, scale=0.5) for q in qs], lag_ratio=0.25)], 1.0),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        eth_old = VGroup(rects[3], tn[3], self.to[3])
        self.steps("The router takes off the courier label, reads the street address, and lowers the time to live from 64 to 63.", [
            (lambda: [*self.uncap(), *[FadeOut(q) for q in qs]], 0.4),
            "takes off",
            (lambda: [peel(eth_old)], 0.8),
            "reads the street",
            (lambda: [Indicate(self.to[2], color=GREEN_M, scale_factor=1.08)], 0.8),
            "lowers the time",
            (lambda: self.set_field("ttl", xfield(2, "TTL 63", YELLOW_M)), 0.6),
        ])
        rects[3] = wrap_rect(3)
        tn[3] = tname(3, "Ethernet", 14)
        self.to[3] = tfield(3, "to the next card", WHITE, mono=False)
        self.steps("Then it sticks on a new label, for the next card on the next link.", [
            "sticks on",
            (lambda: [FadeIn(rects[3], scale=1.05), FadeIn(tn[3]), mac_rt.animate.set_color(GREY_B)], 0.8),
            "for the next card",
            (lambda: [FadeIn(self.to[3], shift=0.1 * DOWN)], 0.5),
        ])
        oks = [mark("new", 3), mark(True, 2), mark(True, 1), mark(True, 0)]
        self.steps("It never opened the envelope. The IP addresses and the ports arrive as they left. Only the label changed.", [
            "never opened",
            (lambda: [glow(rects[1], BLUE_M, 1.01)], 0.7),
            "The IP addresses",
            (lambda: [LaggedStart(*[Create(o) for o in oks[1:]], lag_ratio=0.3)], 0.9),
            "Only the label",
            (lambda: [FadeIn(oks[0], scale=0.6)], 0.5),
        ])
        self.steps("So there never was one long wire. There's a chain of links, and the outer label is rewritten on each one. "
                   "That answers our first question: each machine on the way reads only the street address.", [
            "a chain of links",
            (lambda: [*self.cap("a chain of links: the outer label is rewritten on each one", WHITE), glow(wire, YELLOW_M, 1.0)], 0.8),
            "our first question",
            (lambda: self.cap("1. where to pass it?  Each machine reads only the street address.", WHITE), 0.5),
            "only the street",
            (lambda: [Indicate(self.to[2], color=GREEN_M, scale_factor=1.08)], 0.8),
        ])
        self.steps("A router is the perfect courier: quick, and not the least bit curious. It never reads TCP or HTTP, "
                   "so those layers can change without it noticing.", [
            "not the least bit",
            (lambda: [Wiggle(rt, scale_value=1.05, rotation_angle=0.02 * TAU)], 0.9),
            "It never reads",
            (lambda: [*self.uncap(), glow(rects[1], BLUE_M, 1.01), glow(rects[0], WHITE, 1.01)], 0.8),
            "so those layers",
            (lambda: self.cap("TCP and HTTP can change without any router noticing"), 0.5),
        ])

        # ---------------- scene 6: unwrapping at the server ----------------
        self.steps("The frame reaches the server. Its card keeps it, because the label names that card. "
                   "Now the kernel unwraps, in the opposite order.", [
            (lambda: [*self.uncap(), *[FadeOut(o) for o in oks]], 0.4),
            (lambda: [ride(*L2)], 1.1),
            "Its card keeps",
            (lambda: [glow(srv[0], WHITE, 1.04), Indicate(self.to[3], color=YELLOW_M, scale_factor=1.05)], 0.8),
        ])
        self.steps("How does it know what's inside each wrapper? Here our post office picture needs a patch. "
                   "A paper envelope doesn't say what's in it. Every header here does.", [
            "Here our post",
            (lambda: self.cap("where the post office picture needs a patch"), 0.5),
            "A paper envelope",
            (lambda: self.cap("a paper envelope doesn't say what's inside. Every header here does.", WHITE), 0.5),
        ])
        typ = xfield(3, "type 0x0800", YELLOW_M)
        self.steps("Ethernet's type field says 0x0800: an IP packet is inside. Off comes the label.", [
            (lambda: [FadeIn(typ, shift=0.1 * LEFT), *self.cap("type 0x0800: an IP packet is inside", GOLD_M)], 0.6),
            (lambda: [Indicate(typ, color=YELLOW_M, scale_factor=1.1)], 0.7),
            "Off comes",
            (lambda: [peel(VGroup(rects[3], tn[3], self.to[3], typ)), nouns[3].animate.set_opacity(0.3),
                      *self.set_count(126, "a packet")], 0.8),
        ])
        self.steps("IP's protocol field says 6: a TCP segment is inside. Off comes the parcel.", [
            (lambda: [*self.set_field("ttl", xfield(2, "protocol 6", YELLOW_M)), *self.cap("protocol 6: a TCP segment is inside", GREEN_M)], 0.6),
            (lambda: [Indicate(self.ttl, color=YELLOW_M, scale_factor=1.1)], 0.7),
            "Off comes",
            (lambda: [peel(VGroup(rects[2], tn[2], self.to[2], self.ttl)), nouns[2].animate.set_opacity(0.3),
                      *self.set_count(106, "a segment")], 0.8),
        ])
        self.steps("And TCP's port, 80, picks the program: the web server. It reads exactly the 74 bytes curl wrote. "
                   "That answers our second question.", [
            (lambda: [Indicate(self.to[1], color=YELLOW_M, scale_factor=1.1), *self.cap("port 80: the web server", BLUE_M)], 0.8),
            "It reads",
            (lambda: [peel(VGroup(rects[1], tn[1], self.to[1])), nouns[1].animate.set_opacity(0.3),
                      *self.set_count(74, "a message")], 0.8),
            (lambda: [glow(rects[0], WHITE, 1.02)], 0.7),
            "our second",
            (lambda: self.cap("2. which program?  The port says: 80, the web server.", WHITE), 0.5),
        ])
        self.steps("Every header says what's inside it. The receiver follows the labels, and never guesses.", [
            (lambda: self.cap("every header says what's inside it; the receiver never guesses", YELLOW_M, 28), 0.6),
        ], after=0.6)

        # ---------------- scene 7: two limits ----------------
        self.steps("Two limits. Some boxes on the way do rewrite the street address and the port. "
                   "Lesson 3 of this track meets one.", [
            (lambda: [*self.cap("limit 1: some boxes do rewrite the street address and the port (lesson 3)"),
                      FadeOut(mac_lap), FadeOut(mac_rt)], 0.6),
        ])
        self.steps("And a big answer doesn't fit in one frame. That comes later in this lesson.", [
            (lambda: self.cap("limit 2: a big answer doesn't fit in one frame (later in this lesson)"), 0.6),
        ])

        # ---------------- scene 8: the moral, and a check ----------------
        for k in (1, 2, 3):
            rects[k] = wrap_rect(k)
        tn = {1: tname(1, "TCP", 32), 2: tname(2, "IP", 20), 3: tname(3, "Ethernet", 14)}
        self.to = {1: tfield(1, "to port 80"), 2: tfield(2, "to 104.20.23.154"), 3: tfield(3, "to 22:d2:d5:a2:32:a3")}
        self.ttl = xfield(2, "TTL 64", GREEN_M)

        def rewrap():
            out = []
            for k in (1, 2, 3):
                out.append(AnimationGroup(FadeIn(rects[k], scale=1.05), FadeIn(tn[k]), FadeIn(self.to[k]),
                                          nouns[k].animate.set_opacity(1)))
            return [LaggedStart(*out, lag_ratio=0.5)]

        self.steps("So, one long wire? No. A letter in three wrappers, and a chain of depots that each read only the outside one.", [
            (lambda: [*self.uncap()], 0.3),
            "A letter in three",
            (lambda: [*rewrap(), *self.set_count(140, "a frame")], 1.6),
            (lambda: [FadeIn(self.ttl)], 0.3),
            "a chain of depots",
            (lambda: [glow(rt[0], GREY_B, 1.04), Indicate(self.to[3], color=YELLOW_M, scale_factor=1.05)], 0.8),
        ])
        self.steps("On the way down, each layer adds a header. On the way up, each layer reads one, and takes it off.", [
            (lambda: self.cap("down: each layer adds a header.   up: each layer reads one and takes it off.", WHITE), 0.6),
        ])
        R1X, R2X = -1.6, 1.6
        rt2 = machine("router", "another depot", R2X, MY, GREY_B, w=RW, mono=False)
        self.steps("One quick check. Put a second router on the path. When the frame leaves it, what will the time to live say? "
                   "Pause and think.", [
            (lambda: self.uncap(), 0.3),
            "Put a second",
            (lambda: [rt.animate.move_to([R1X, MY, 0]), FadeIn(rt2, shift=0.3 * DOWN)], 0.9),
            "the time to live",
            (lambda: [Indicate(self.ttl, color=YELLOW_M, scale_factor=1.15)], 0.7),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("62. Each router lowers it by one, and puts on a new label. Everything inside the label arrives as it left.", [
            (lambda: [*self.uncap(), ride(LAP_X + MW / 2 + 0.05, R1X - RW / 2 - 0.05)], 0.6),
            (lambda: [*self.set_field("ttl", xfield(2, "TTL 63", YELLOW_M)), ride(R1X + RW / 2 + 0.05, R2X - RW / 2 - 0.05)], 0.6),
            (lambda: [*self.set_field("ttl", xfield(2, "TTL 62", YELLOW_M)), ride(R2X + RW / 2 + 0.05, SRV_X - MW / 2 - 0.05)], 0.6),
            "puts on a new",
            (lambda: [glow(rects[3], GOLD_M, 1.01)], 0.7),
            "Everything inside",
            (lambda: [glow(rects[2], GREEN_M, 1.01), glow(rects[1], BLUE_M, 1.01), glow(rects[0], WHITE, 1.01)], 0.8),
        ], after=0.3)
        self.play(*self.cap("each layer adds a header on the way down, and reads one on the way up", YELLOW_M, 26), run_time=0.6)
        self.wait(2.0)
