from sfz import *

# Applied in this order, before the course-wide rules.
SAY[0:0] = [
    (r"\brouter2\b", "router two"),
    (r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b", r"\1 dot \2 dot \3 dot \4"),
    (r"/(\d+)\b", r" slash \1"),
    (r"\bBGP\b", "B G P"),
]

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
TOP, LOW = 2.3, 0.65                   # the two rows of machines
BUS = 1.35                             # the lan, a shared wire under the top row
BW, BH = 2.3, 0.9
X_CL, X_RT, X_R2, X_LG = -5.45, -1.4, 2.0, 5.35
X_GW, X_PR, X_SV = -5.45, -3.2, 0.1
RT_BUS, RT_WAN = -1.9, -0.6            # where router's lan and wan wires leave its box
TB_X, TB_Y0, TB_DY = -5.6, -0.68, 0.42
CAP_Y, BAR_Y = -2.95, -3.4

P_CL_RT = [[X_CL, TOP - BH / 2, 0], [X_CL, BUS, 0], [RT_BUS, BUS, 0], [RT_BUS, TOP - BH / 2, 0]]
P_CL_PR = [[X_CL, TOP - BH / 2, 0], [X_CL, BUS, 0], [X_PR, BUS, 0], [X_PR, LOW + BH / 2, 0]]
P_CL_GW = [[X_CL, TOP - BH / 2, 0], [X_GW, LOW + BH / 2, 0]]
P_RT_R2 = [[X_RT + BW / 2, TOP, 0], [X_R2 - BW / 2, TOP, 0]]
P_R2_LG = [[X_R2 + BW / 2, TOP, 0], [X_LG - BW / 2, TOP, 0]]
P_RT_SV = [[RT_WAN, TOP - BH / 2, 0], [RT_WAN, LOW + BH / 2, 0]]


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


def go(pts, color=YELLOW_M, rt=0.9):
    """A dot (the packet) running along a wire."""
    d = Dot(radius=0.09, color=color).move_to(pts[0]).set_z_index(3)
    path = VMobject().set_points_as_corners(pts)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, path, rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.12))


def wire(pts):
    return VMobject(stroke_color=GREY_B, stroke_width=2.5).set_points_as_corners(pts).set_z_index(-5)


# ---- the pieces ----
def node(name, sub, x, y, w=BW, color=WHITE, mono=True, size=22):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=BH, stroke_color=color, stroke_width=3).set_fill(BLACK, 1)
    r.move_to([x, y, 0])
    s = M(sub, 16, GREY_B) if mono else T(sub, 17, GREY_B)
    return VGroup(r, T(name, size).move_to([x, y + 0.17, 0]), s.move_to([x, y - 0.2, 0]))


def trow(i, prefix, dest, color=WHITE):
    y = TB_Y0 - i * TB_DY
    return VGroup(left_at(M(prefix, 19, color), TB_X, y), T("→", 20, GREY_B).move_to([TB_X + 2.75, y, 0]),
                  left_at(T(dest, 19, color), TB_X + 3.1, y))


def hl(row, color=YELLOW_M):
    return SurroundingRectangle(row, buff=0.08, corner_radius=0.06, color=color, stroke_width=2.5)


class Routing(Base):
    """net-04, section 0. A packet from client to ledger (10.10.4.40) crosses router and router2; each forwards it
    alone, like parcel sorting offices. One default line can't serve a router with three ways out, so it keeps one line
    per block (10.10.4.0/24: first 24 bits fixed). Client's lines /0, /16 and /24 all fit peer's 10.10.1.20; reading
    the list top-down would send it to Docker's gateway, but the longest prefix wins and the order never matters."""

    def set_rows(self, rows):
        olds = [r for r in self.rows]
        self.rows = rows
        return [*[FadeOut(r) for r in olds], LaggedStart(*[FadeIn(r, shift=0.1 * RIGHT) for r in rows], lag_ratio=0.25)]

    def set_title(self, s):
        new = left_at(T(s, 20, GREY_B), TB_X, -0.25)
        old, self.tt = self.tt, new
        return [swap(old, new)]

    def construct(self):
        self.capm = self.tt = None
        self.rows = []
        self.title_card("The most specific route wins", "how a router picks the next step for every packet")

        # ---------------- scene 1: who knows the way? ----------------
        cl = node("client", "10.10.1.10", X_CL, TOP)
        rt = node("router", "10.10.1.2", X_RT, TOP, color=GREY_B)
        r2 = node("router2", "10.10.3.3", X_R2, TOP, color=GREY_B)
        lg = node("ledger", "10.10.4.40", X_LG, TOP)
        pr = node("peer", "10.10.1.20", X_PR, LOW, w=1.6)
        sv = node("server", "10.10.2.20", X_SV, LOW, w=2.0)
        gw = node("Docker's gateway", "10.10.1.1", X_GW, LOW, w=2.25, size=19)
        bus = Line([X_GW - 0.55, BUS, 0], [RT_BUS, BUS, 0], stroke_width=2.5, color=GREY_B).set_z_index(-5)
        stubs = VGroup(wire([[X_CL, TOP - BH / 2, 0], [X_CL, BUS, 0]]), wire([[RT_BUS, BUS, 0], [RT_BUS, TOP - BH / 2, 0]]))
        lan_t = T("lan", 17, GREY_C).move_to([-2.55, BUS + 0.18, 0])
        tun = VGroup(wire(P_RT_R2), T("tunnel", 17, GREY_C).move_to([(X_RT + X_R2) / 2, TOP + 0.24, 0]))
        dc = VGroup(wire(P_R2_LG), T("dc", 17, GREY_C).move_to([(X_R2 + X_LG) / 2, TOP + 0.24, 0]))
        wan = VGroup(wire(P_RT_SV), T("wan", 17, GREY_C).move_to([RT_WAN + 0.32, (TOP + LOW) / 2, 0]))
        lowers = VGroup(wire([[X_PR, BUS, 0], [X_PR, LOW + BH / 2, 0]]), wire([[X_GW, BUS, 0], [X_GW, LOW + BH / 2, 0]]))
        pkt = VGroup(RoundedRectangle(corner_radius=0.08, width=3.3, height=0.42, stroke_color=YELLOW_M, stroke_width=2.5)
                     .set_fill("#1c1a10", 1), M("packet: to 10.10.4.40", 16, YELLOW_M)).move_to([X_CL + 0.7, 3.17, 0])
        pkt[1].move_to(pkt[0])
        self.steps("Client wants to send a packet to ledger, at 10.10.4.40, the computer that keeps the café's payment records.", [
            (lambda: [FadeIn(cl), FadeIn(lg)], 0.8),
            "a packet",
            (lambda: [FadeIn(pkt, shift=0.1 * DOWN)], 0.5),
        ])
        self.steps("A packet is a small piece of data with a label in front: where it came from, and where it's going.", [
            (lambda: self.cap("a packet: a small piece of data, with a label saying where it's from and where it's going"), 0.5),
            "where it's going",
            (lambda: [Indicate(pkt[1], color=YELLOW_M, scale_factor=1.08)], 0.7),
        ])
        self.steps("On the way, it crosses two routers: machines joined to more than one network, whose job is to pass packets on.", [
            (lambda: [*self.uncap(), FadeIn(rt), FadeIn(r2)], 0.7),
            (lambda: [Create(bus), Create(stubs), FadeIn(lan_t), Create(tun), Create(dc)], 0.9),
            "machines joined",
            (lambda: [FadeIn(sv), Create(wan), FadeIn(pr), FadeIn(gw), Create(lowers)], 0.9),
            "pass packets on",
            (lambda: self.cap("a router: a machine on more than one network that passes packets on"), 0.5),
        ])
        self.steps("Nobody on the way knows the whole path. So how does each router know which way to send it?", [
            (lambda: self.uncap(), 0.3),
            "which way",
            (lambda: [glow(rt[0], YELLOW_M), glow(r2[0], YELLOW_M)], 0.8),
            (lambda: self.cap("how does each router know which way to send it?", WHITE), 0.5),
        ])

        # ---------------- scene 2: sorting offices ----------------
        self.steps("Think of a chain of parcel sorting offices. A sorter reads the address, drops the parcel in the van "
                   "for the right direction, and never thinks about it again.", [
            (lambda: self.cap("a chain of parcel sorting offices"), 0.5),
            "drops the parcel",
            (lambda: [go(P_CL_RT, YELLOW_M, 1.1)], 1.1),
            (lambda: [glow(rt[0], YELLOW_M)], 0.5),
            "never thinks",
            (lambda: [go(P_RT_R2, YELLOW_M, 0.7)], 0.7),
        ])
        self.steps("Routers work the same way. Each one reads the destination, hands the packet to the next machine, and forgets it.", [
            "Each one reads",
            (lambda: [glow(r2[0], YELLOW_M)], 0.5),
            "hands the packet",
            (lambda: [go(P_R2_LG, YELLOW_M, 0.7)], 0.7),
            "forgets it",
            (lambda: [glow(lg[0], WHITE)], 0.5),
        ])
        self.steps("That hand-off is called forwarding, and the next machine is the next hop.", [
            (lambda: self.cap("forwarding: hand the packet to the next machine, the next hop", WHITE), 0.6),
        ])
        self.steps("A sorter never asks a parcel where it's been. Nobody has the time. "
                   "So each router decides with one thing in hand: the destination.", [
            "So each router",
            (lambda: [*self.cap("each router decides with one thing in hand: the destination"), Indicate(pkt[1], color=YELLOW_M, scale_factor=1.08)], 0.8),
        ])

        # ---------------- scene 3: the simplest table, and where it breaks ----------------
        self.steps("It decides from a list called its routing table. Start with the simplest list that could work: one line. "
                   "Everything goes to my gateway, the router that leads out.", [
            (lambda: [*self.uncap(), *self.set_title("router's table")], 0.5),
            "one line",
            (lambda: self.set_rows([trow(0, "everything", "my gateway")]), 0.7),
        ])
        self.steps("That's the default route. For a machine with one way out, it's all you need.", [
            (lambda: self.cap("the default route: everything else goes this way"), 0.5),
        ])
        self.steps("But router has three ways out. A packet for the server must leave on wan. One for ledger must go into the tunnel. "
                   "One line can't say both.", [
            (lambda: [*self.uncap(), glow(rt[0], WHITE)], 0.6),
            "for the server",
            (lambda: [go(P_RT_SV, WHITE, 0.6), glow(sv[0], WHITE)], 0.7),
            "into the tunnel",
            (lambda: [go(P_RT_R2, YELLOW_M, 0.6)], 0.7),
            "One line can't",
            (lambda: [*self.cap("one line, three ways out: it can't work", RED_M), self.rows[0].animate.set_color(RED_M)], 0.6),
        ])

        # ---------------- scene 4: blocks, and router's real table ----------------
        bx = [2.35, 3.4, 4.45, 5.75]
        nums = VGroup()
        for i, (s, x) in enumerate(zip(["10", "10", "4", "0 to 255"], bx)):
            w = 1.45 if i == 3 else 0.95
            col = GREY_B if i == 3 else GREEN_M
            r = RoundedRectangle(corner_radius=0.08, width=w, height=0.55, stroke_color=col, stroke_width=2.5).move_to([x, -0.85, 0])
            t = (T(s, 17, GREY_B) if i == 3 else M(s, 20, GREEN_M)).move_to(r)
            nums.add(VGroup(r, t, T("8 bits", 14, GREY_C).move_to([x, -1.32, 0])))
        bhead = M("10.10.4.0/24", 22).move_to([4.05, -0.25, 0])
        bfix = T("/24: the first 24 bits are fixed", 18, GREEN_M).move_to([4.05, -1.78, 0])
        brange = M("10.10.4.0 to 10.10.4.255", 17).move_to([4.05, -2.2, 0])
        self.steps("So a router keeps one line per block of addresses. A block is written like this: 10.10.4.0/24.", [
            (lambda: self.uncap(), 0.3),
            "A block is",
            (lambda: [FadeIn(bhead, shift=0.1 * DOWN)], 0.6),
        ])
        self.steps("An address is 32 bits, 8 for each of its four numbers. The /24 says the first 24 bits, "
                   "here the first three numbers, are fixed.", [
            "An address",
            (lambda: [LaggedStart(*[FadeIn(n, shift=0.1 * UP) for n in nums], lag_ratio=0.2)], 1.0),
            "The /24",
            (lambda: [FadeIn(bfix)], 0.5),
            "the first three",
            (lambda: [LaggedStart(*[glow(n[0], GREEN_M, 1.08) for n in nums[:3]], lag_ratio=0.25)], 0.9),
        ])
        self.steps("So the block holds every address from 10.10.4.0 to 10.10.4.255. That count of fixed bits is the prefix length.", [
            "every address",
            (lambda: [FadeIn(brange), glow(nums[3][0], WHITE, 1.06)], 0.6),
            "prefix length",
            (lambda: self.cap("prefix length: how many bits are fixed (here 24)", WHITE), 0.5),
        ])
        rrows = [trow(0, "10.10.1.0/24", "lan, its own card"), trow(1, "10.10.2.0/24", "wan, its own card"),
                 trow(2, "10.10.3.0/24", "tunnel, its own card"), trow(3, "10.10.4.0/24", "via router2 (10.10.3.3)"),
                 trow(4, "0.0.0.0/0", "Docker's gateway (10.10.1.1)")]
        self.steps("Router's table gets a line for each of its own cards, which the kernel adds by itself, a line typed in by hand "
                   "for ledger's block, and the default, now written 0.0.0.0/0: no fixed bits at all, so every address fits.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(nums, bfix, brange)), bhead.animate.set_opacity(0)], 0.5),
            (lambda: self.set_rows(rrows[:3]), 0.9),
            "a line typed",
            (lambda: [FadeIn(rrows[3], shift=0.1 * RIGHT)], 0.5),
            "and the default",
            (lambda: [FadeIn(rrows[4], shift=0.1 * RIGHT)], 0.5),
            "no fixed bits",
            (lambda: [Indicate(rrows[4][0], color=YELLOW_M, scale_factor=1.08)], 0.7),
        ])
        self.rows = rrows
        box4 = hl(rrows[3])
        self.steps("Watch ledger's packet arrive. 10.10.4.40 fits 10.10.4.0/24, so router sends it into the tunnel, to router2.", [
            (lambda: [go(P_CL_RT, YELLOW_M, 1.0)], 1.0),
            "fits 10.10",
            (lambda: [Create(box4)], 0.5),
            "into the tunnel",
            (lambda: [go(P_RT_R2, YELLOW_M, 0.7)], 0.7),
        ])
        box0 = hl(rrows[4], GREY_B)
        self.steps("Notice it also fits the default. Hold that thought.", [
            "also fits",
            (lambda: [Create(box0)], 0.5),
        ], after=0.4)

        # ---------------- scene 5: three lines fit; which wins? ----------------
        crows = [trow(0, "0.0.0.0/0", "Docker's gateway (10.10.1.1)"), trow(1, "10.10.0.0/16", "router (10.10.1.2)"),
                 trow(2, "10.10.1.0/24", "straight across lan")]
        self.steps("Now look at client's table. The lesson gives it a broad line: every address in 10.10.0.0/16 goes to router. "
                   "Client already had its own network, 10.10.1.0/24, straight across lan, and the default.", [
            (lambda: [FadeOut(box4), FadeOut(box0), *self.set_title("client's table, in the order it prints")], 0.5),
            (lambda: [*[FadeOut(r) for r in self.rows]], 0.4),
            "a broad line",
            (lambda: [FadeIn(crows[1], shift=0.1 * RIGHT), glow(cl[0], WHITE)], 0.6),
            "its own network",
            (lambda: [FadeIn(crows[2], shift=0.1 * RIGHT)], 0.5),
            "and the default",
            (lambda: [FadeIn(crows[0], shift=0.1 * RIGHT)], 0.5),
        ])
        self.rows = crows
        ppk = VGroup(RoundedRectangle(corner_radius=0.08, width=3.3, height=0.42, stroke_color=YELLOW_M, stroke_width=2.5)
                     .set_fill("#1c1a10", 1), M("packet: to 10.10.1.20", 16, YELLOW_M)).move_to(pkt)
        ppk[1].move_to(ppk[0])
        fits = [T("fits", 17, YELLOW_M).move_to([1.3, TB_Y0 - i * TB_DY, 0]) for i in range(3)]
        self.steps("A packet for peer, at 10.10.1.20, fits all three. Which line wins? Pause and guess.", [
            (lambda: [swap(pkt, ppk), glow(pr[0], YELLOW_M)], 0.7),
            "fits all three",
            (lambda: [LaggedStart(*[FadeIn(f) for f in fits], lag_ratio=0.3)], 0.8),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        first = hl(crows[0], RED_M)
        self.steps("Most lists, we read from the top and stop at the first line that fits. Here, that's the default. "
                   "So peer's packet would go to Docker's gateway, the way out to the internet, to reach a computer on client's own wire.", [
            (lambda: self.uncap(), 0.3),
            "stop at the first",
            (lambda: [Create(first)], 0.5),
            "So peer's packet",
            (lambda: [go(P_CL_GW, RED_M, 0.8), glow(gw[0], RED_M)], 0.9),
            "to reach a computer",
            (lambda: [glow(pr[0], WHITE)], 0.7),
        ])
        self.steps("Well... that's like posting a note to your neighbour through the national hub.", [
            (lambda: self.cap("posting a note to your neighbour through the national hub", RED_M), 0.5),
        ], after=0.4)
        bits = [T(s, 17, GREY_B).move_to([1.3, TB_Y0 - i * TB_DY, 0]) for i, s in enumerate(["0 bits", "16 bits", "24 bits"])]
        win = hl(crows[2], GREEN_M)
        self.steps("The real rule is longest prefix match. Of all the lines that fit, the one with the most fixed bits wins, "
                   "because it describes the destination most precisely.", [
            (lambda: [*self.cap("longest prefix match: of the lines that fit, the most fixed bits wins", WHITE), FadeOut(first)], 0.6),
            "the most fixed bits",
            (lambda: [*[swap(f, b) for f, b in zip(fits, bits)]], 0.7),
            "most precisely",
            (lambda: [Create(win), bits[2].animate.set_color(GREEN_M)], 0.6),
        ])
        self.steps("24 beats 16, which beats 0. So peer's packet goes straight across lan, and ledger's goes to router. "
                   "And the order of the lines never matters.", [
            "24 beats",
            (lambda: [Indicate(bits[2], color=GREEN_M), Indicate(bits[1], color=WHITE), Indicate(bits[0], color=WHITE)], 0.8),
            "goes straight across",
            (lambda: [go(P_CL_PR, GREEN_M, 0.9)], 0.9),
            "ledger's goes",
            (lambda: [go(P_CL_RT, YELLOW_M, 0.9)], 0.9),
            "the order",
            (lambda: [*self.cap("the order of the lines never matters"), *[glow(win, GREEN_M, 1.02)]], 0.7),
        ])
        self.steps("A sorting office works the same way. The pigeonhole for one street beats the one for the whole city, "
                   "which beats everything else: send it to the national hub.", [
            (lambda: self.cap("one street  >  the whole city  >  everything else"), 0.5),
            "one street",
            (lambda: [Indicate(crows[2], color=GREEN_M, scale_factor=1.04)], 0.6),
            "the whole city",
            (lambda: [Indicate(crows[1], color=WHITE, scale_factor=1.04)], 0.6),
            "everything else",
            (lambda: [Indicate(crows[0], color=WHITE, scale_factor=1.04)], 0.6),
        ])

        # ---------------- scene 6: where lines come from, and the limit ----------------
        self.steps("On the internet, nobody types these lines in. Routers tell each other which blocks they can reach, "
                   "using a routing protocol called BGP. A full table holds around a million blocks.", [
            (lambda: [*self.cap("on the internet: routers announce their blocks to each other (BGP)"), FadeOut(win)], 0.6),
            "A full table",
            (lambda: self.cap("a full table: around a million blocks"), 0.5),
        ])
        self.steps("One property matters for what comes next. Each router decides alone, with no memory of where the packet has been.", [
            (lambda: self.cap("each router decides alone, with no memory of the packet", WHITE), 0.5),
            "decides alone",
            (lambda: [glow(rt[0], YELLOW_M), glow(r2[0], YELLOW_M)], 0.8),
        ])
        self.steps("That lets the internet route around a broken link. It also means two routers whose tables disagree "
                   "could pass a packet back and forth forever. The next section makes two of them do it.", [
            "back and forth",
            (lambda: [go(P_RT_R2, RED_M, 0.5)], 0.5),
            (lambda: [go(list(reversed(P_RT_R2)), RED_M, 0.5)], 0.5),
            (lambda: [go(P_RT_R2, RED_M, 0.5)], 0.5),
            "The next section",
            (lambda: self.cap("a packet bouncing forever: the next section", RED_M), 0.5),
        ])

        # ---------------- scene 7: the moral, and a check ----------------
        self.steps("So how does a router know the way? It doesn't. It knows the next step: the most specific line that fits.", [
            (lambda: self.cap("how does a router know the way?", WHITE), 0.5),
            "It knows the next",
            (lambda: [*self.cap("it knows only the next step: the most specific line that fits", YELLOW_M, 28), go(P_CL_RT, YELLOW_M, 0.8)], 0.8),
        ], after=0.5)
        qpk = VGroup(RoundedRectangle(corner_radius=0.08, width=3.3, height=0.42, stroke_color=YELLOW_M, stroke_width=2.5)
                     .set_fill("#1c1a10", 1), M("packet: to 1.1.1.1", 16, YELLOW_M)).move_to(pkt)
        qpk[1].move_to(qpk[0])
        self.steps("One quick check. Client sends a packet to 1.1.1.1, out on the internet. Which of client's three lines wins? "
                   "Pause and think.", [
            (lambda: [*self.uncap(), swap(ppk, qpk), *[FadeOut(b) for b in bits]], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        ans = hl(crows[0], GREEN_M)
        self.steps("The default. 1.1.1.1 doesn't start with 10.10, so the only line that fits is 0.0.0.0/0. Off to Docker's gateway.", [
            (lambda: [*self.uncap(), Create(ans)], 0.6),
            "Off to",
            (lambda: [go(P_CL_GW, GREEN_M, 0.8), glow(gw[0], GREEN_M)], 0.9),
        ], after=0.3)
        self.play(*self.cap("most specific line wins; the order never matters", YELLOW_M, 28), run_time=0.6)
        self.wait(2.0)
