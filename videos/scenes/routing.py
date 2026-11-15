from sfz import *

SAY.insert(0, (r"\brouter2\b", "router two"))
SAY.insert(0, (r"\bICMP\b", "I C M P"))
SAY.insert(0, (r"\b([Tt])raceroute\b", r"\1race route"))
SAY.insert(0, (r"\b10\.10\.4\b", "ten dot ten dot four"))
SAY.insert(0, (r"\b10\.10\.4\.0/24\b", "ten dot ten dot four dot zero slash twenty-four"))

HY, HW, HH = 2.75, 2.4, 1.1                 # the path, left to right
HX = {"client": -5.4, "router": -1.85, "router2": 1.75, "ledger": 5.3}
NET_Y = 1.05                                # the internet, below router
TX, TW, TY, TH = -2.75, 7.3, -0.95, 2.6     # routing table panel
PX, PW = 3.9, 5.0                           # packet / traceroute panel
ROW_Y = [TY + 0.05, TY - 0.45, TY - 0.95]
LINE_Y = [TY + 0.3, TY - 0.15, TY - 0.6, TY - 1.02]
ST_Y = -3.0


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def run(a, b, color=YELLOW_M, run_time=0.7):
    """A dot from point a to point b, invisible until its turn."""
    d = Dot(radius=0.08, color=color).move_to(a).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.12))


def edge(a, b):
    """The points where the link between hosts a and b leaves each box."""
    s = 1 if HX[b] > HX[a] else -1
    return np.array([HX[a] + s * HW / 2, HY, 0]), np.array([HX[b] - s * HW / 2, HY, 0])


def hop(a, b, color=YELLOW_M, rt=0.6):
    pa, pb = edge(a, b)
    return run(pa, pb, color, rt)


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


def host(name, ip, color):
    x = HX[name]
    r = RoundedRectangle(corner_radius=0.14, width=HW, height=HH, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1)
    r.move_to([x, HY, 0])
    return VGroup(r, T(name, 28).move_to([x, HY + 0.2, 0]), M(ip, 21, GREY_B).move_to([x, HY - 0.22, 0]))


def row(dest, nxt, k, color=WHITE):
    return VGroup(left_at(M(dest, 22, color), TX - TW / 2 + 0.3, ROW_Y[k]), left_at(M(nxt, 22, color), TX - 0.35, ROW_Y[k]))


def pline(s, k, color=WHITE, size=22):
    return left_at(M(s, size, color), PX - PW / 2 + 0.3, LINE_Y[k])


def ptitle(s):
    return T(s, 24, GREY_B).move_to([PX, TY + TH / 2 - 0.35, 0])


def status(s, color=GREY_B):
    return T(s, 28, color).move_to([0, ST_Y, 0])


class Routing(Base):
    """net-04, sections 0 to 2: client sends to ledger (10.10.4.40) through router and router2. A table with only a default
    route sends it to the internet; a /24 line for 10.10.4.0 wins by longest prefix match. Two routers that disagree loop a
    packet; the TTL (5 here) runs out at router, which sends ICMP time exceeded. Traceroute's probes with TTL 1, 2, 3 map
    the hops 10.10.1.2, 10.10.3.3 and 10.10.4.40, the last by port unreachable."""

    def construct(self):
        self.title_card("Routing, TTL and traceroute", "one table lookup per hop, and a counter that stops loops")

        hs = {"client": host("client", "10.10.1.10", BLUE_M), "router": host("router", "10.10.1.2", GOLD_M),
              "router2": host("router2", "10.10.3.3", GOLD_M), "ledger": host("ledger", "10.10.4.40", GREEN_M)}
        links = VGroup(*[Line(*edge(a, b), stroke_width=3, color=GREY_C)
                         for a, b in (("client", "router"), ("router", "router2"), ("router2", "ledger"))])
        lnames = VGroup(*[T(s, 20, GREY_B).move_to([(HX[a] + HX[b]) / 2, HY + 0.25, 0])
                          for s, (a, b) in zip(("lan", "tunnel", "dc"), (("client", "router"), ("router", "router2"),
                                                                         ("router2", "ledger")))])
        net = RoundedRectangle(corner_radius=0.14, width=HW, height=0.7, stroke_color=GREY_B, stroke_width=2.5)
        net.set_fill(BLACK, 1).move_to([HX["router"], NET_Y, 0])
        netl = T("internet", 24, GREY_B).move_to(net)
        wan = Line([HX["router"], HY - HH / 2, 0], [HX["router"], NET_Y + 0.35, 0], stroke_width=3, color=GREY_C)
        wanl = T("wan", 20, GREY_B).move_to([HX["router"] + 0.38, (HY - HH / 2 + NET_Y + 0.35) / 2, 0])

        tpanel = RoundedRectangle(corner_radius=0.14, width=TW, height=TH, stroke_color=GOLD_M, stroke_width=2.5)
        tpanel.set_fill(BLACK, 1).move_to([TX, TY, 0])
        ttitle = T("router's routing table", 24, GREY_B).move_to([TX, TY + TH / 2 - 0.35, 0])
        thead = VGroup(left_at(T("destination block", 20, GREY_C), TX - TW / 2 + 0.3, TY + 0.5),
                       left_at(T("next hop", 20, GREY_C), TX - 0.35, TY + 0.5))
        ppanel = RoundedRectangle(corner_radius=0.14, width=PW, height=TH, stroke_color=BLUE_M, stroke_width=2.5)
        ppanel.set_fill(BLACK, 1).move_to([PX, TY, 0])
        pt = ptitle("the packet")
        pto = pline("to   10.10.4.40", 0)
        pttl = pline("TTL  64", 1, GREY_B)
        self.steps("A packet from client to ledger crosses two routers, and nobody on the way knows the whole path. "
                   "Each router looks at the destination, picks the next hop from its routing table, and forgets the packet.", [
            (lambda: [*[FadeIn(h) for h in hs.values()], Create(links), FadeIn(lnames)], 1.0),
            (lambda: [FadeIn(ppanel), FadeIn(pt), FadeIn(pto), FadeIn(pttl)], 0.7),
            "Each router",
            (lambda: [glow(hs["router"][0], GOLD_M), pto.animate.set_color(YELLOW_M)], 0.8),
            "from its routing table",
            (lambda: [FadeIn(tpanel), FadeIn(ttitle), FadeIn(thead), pto.animate.set_color(WHITE)], 0.8),
        ])

        rdef = row("0.0.0.0/0", "internet gateway", 2)
        xnet = tick(False, 0.2).move_to([HX["router"] + 1.55, NET_Y, 0])
        self.steps("The simplest table has one line, the default route: everything goes to my gateway. "
                   "For router, that sends ledger's packet out to the internet.", [
            (lambda: [FadeIn(rdef, shift=0.1 * DOWN)], 0.7),
            "For router",
            (lambda: [FadeIn(net), FadeIn(netl), Create(wan), FadeIn(wanl)], 0.7),
            (lambda: [hop("client", "router", BLUE_M, 0.6)], 0.6),
            (lambda: [run(wan.get_start(), wan.get_end(), RED_M, 0.6), rdef.animate.set_color(RED_M)], 0.6),
            (lambda: [Create(xnet)], 0.4),
        ])

        r1 = row("10.10.1.0/24", "lan, direct", 0)
        r4 = row("10.10.4.0/24", "router2, 10.10.3.3", 1, GOLD_M)
        self.steps("So a router keeps one line per block of addresses. 10.10.4.0/24 means every address "
                   "whose first 24 bits are 10.10.4, and that block is behind router2.", [
            (lambda: [FadeOut(xnet), rdef.animate.set_color(WHITE), FadeIn(r1, shift=0.1 * DOWN)], 0.7),
            "10.10.4.0/24",
            (lambda: [FadeIn(r4, shift=0.1 * DOWN)], 0.7),
            "whose first 24 bits",
            (lambda: [r4[0].animate(rate_func=there_and_back).scale(1.12)], 0.9),
            "and that block",
            (lambda: [glow(hs["router2"][0], GOLD_M)], 0.8),
        ])

        win = chip("longest prefix: /24 beats /0", GOLD_M, 24).move_to([0, ST_Y, 0])
        self.steps("Now ledger's address matches two lines. The longest prefix wins: the line with the most matching bits, "
                   "because it knows the destination best.", [
            (lambda: [pto.animate.set_color(YELLOW_M), r4.animate.set_color(YELLOW_M), rdef.animate.set_color(YELLOW_M),
                      r1.animate.set_color(GREY_D)], 0.8),
            "The longest prefix",
            (lambda: [r4.animate.set_color(GOLD_M).scale(1.05), rdef.animate.set_color(GREY_D)], 0.8),
            (lambda: [FadeIn(win, shift=0.1 * UP)], 0.6),
        ])

        self.steps("So router hands the packet to router2, which does the same, and it reaches ledger.", [
            (lambda: [r4.animate.scale(1 / 1.05), hop("router", "router2", GOLD_M, 0.8)], 0.8),
            (lambda: [hop("router2", "ledger", GREEN_M, 0.8)], 0.8),
            (lambda: [glow(hs["ledger"][0], GREEN_M), pto.animate.set_color(GREEN_M)], 0.8),
        ])

        lr = pline("router:  10.10.9.0/24 → router2", 2, GOLD_M, 17)
        lr2 = pline("router2: 10.10.9.0/24 → router", 3, GOLD_M, 17)
        self.steps("Each router decides alone. If two routers disagree about a block, "
                   "they pass a packet back and forth forever.", [
            (lambda: [FadeOut(win), r1.animate.set_color(WHITE), r4.animate.set_color(WHITE), rdef.animate.set_color(WHITE),
                      Transform(pto, pline("to   10.10.9.9", 0)), FadeOut(net), FadeOut(netl), FadeOut(wan), FadeOut(wanl)], 0.8),
            "If two routers",
            (lambda: [FadeIn(lr, shift=0.1 * DOWN)], 0.5),
            (lambda: [FadeIn(lr2, shift=0.1 * DOWN)], 0.5),
            "back and forth",
            (lambda: [hop("router", "router2", RED_M, 0.45)], 0.45),
            (lambda: [hop("router2", "router", RED_M, 0.45)], 0.45),
            (lambda: [hop("router", "router2", RED_M, 0.45)], 0.45),
            (lambda: [hop("router2", "router", RED_M, 0.45)], 0.45),
        ])

        self.steps("So the IP header carries a counter, the TTL. Every router lowers it by one before it forwards. "
                   "Client sends this packet with TTL 5.", [
            (lambda: [pttl.animate.set_color(YELLOW_M)], 0.6),
            "Every router",
            (lambda: [Transform(pttl, pline("TTL  64 → 63", 1, YELLOW_M))], 0.8),
            "Client sends",
            (lambda: [Transform(pttl, pline("TTL  5", 1, YELLOW_M))], 0.6),
            (lambda: [hop("client", "router", BLUE_M, 0.6)], 0.6),
        ])

        drop = tick(False, 0.2).move_to([HX["router"], HY - HH / 2 - 0.3, 0])
        icmp = VGroup(pline("ICMP time exceeded", 2, TEAL_M), pline("from 10.10.1.2", 3, TEAL_M))

        def bounce(a, b, ttl):
            return [hop(a, b, RED_M, 0.5), Transform(pttl, pline(f"TTL  {ttl}", 1, YELLOW_M))]

        self.steps("4, 3, 2, 1. A router may not forward a packet that would arrive with 0, so it drops it, "
                   "and sends an ICMP time exceeded message back to the sender.", [
            (lambda: bounce("router", "router2", 4), 0.5),
            (lambda: bounce("router2", "router", 3), 0.5),
            (lambda: bounce("router", "router2", 2), 0.5),
            (lambda: bounce("router2", "router", 1), 0.5),
            "A router may not",
            (lambda: [Create(drop), pttl.animate.set_color(RED_M)], 0.5),
            "and sends",
            (lambda: [FadeOut(lr2), FadeOut(lr), hop("router", "client", TEAL_M, 0.8)], 0.8),
            (lambda: [FadeIn(icmp, shift=0.1 * UP)], 0.5),
        ])

        tr = [pline(" 1  10.10.1.2   router", 1), pline(" 2  10.10.3.3   router2", 2), pline(" 3  10.10.4.40  ledger", 3)]
        probe = pline("probe: TTL 1", 0, YELLOW_M)
        self.steps("Traceroute uses exactly this. Its first probe has TTL 1. "
                   "Router drops it and reports back, so hop 1 is router.", [
            (lambda: [FadeOut(drop), FadeOut(icmp), FadeOut(pttl), FadeOut(pto),
                      Transform(pt, ptitle("traceroute to 10.10.4.40"))], 0.7),
            "Its first probe",
            (lambda: [FadeIn(probe)], 0.5),
            (lambda: [hop("client", "router", YELLOW_M, 0.6)], 0.6),
            "Router drops it",
            (lambda: [hop("router", "client", TEAL_M, 0.6)], 0.6),
            "so hop 1",
            (lambda: [FadeIn(tr[0], shift=0.1 * UP), glow(hs["router"][0], TEAL_M)], 0.7),
        ])

        self.steps("The next probe has TTL 2 and dies one router further. Hop 2 is router2.", [
            (lambda: [Transform(probe, pline("probe: TTL 2", 0, YELLOW_M))], 0.4),
            (lambda: [hop("client", "router", YELLOW_M, 0.5)], 0.5),
            (lambda: [hop("router", "router2", YELLOW_M, 0.5)], 0.5),
            (lambda: [hop("router2", "router", TEAL_M, 0.5)], 0.5),
            (lambda: [hop("router", "client", TEAL_M, 0.5)], 0.5),
            "Hop 2",
            (lambda: [FadeIn(tr[1], shift=0.1 * UP), glow(hs["router2"][0], TEAL_M)], 0.7),
        ])

        self.steps("TTL 3 reaches ledger itself. Nothing listens on the probe's port, so ledger answers port unreachable, "
                   "and traceroute knows it has arrived.", [
            (lambda: [Transform(probe, pline("probe: TTL 3", 0, YELLOW_M))], 0.4),
            (lambda: [hop("client", "router", YELLOW_M, 0.45)], 0.45),
            (lambda: [hop("router", "router2", YELLOW_M, 0.45)], 0.45),
            (lambda: [hop("router2", "ledger", YELLOW_M, 0.45)], 0.45),
            "Nothing listens",
            (lambda: [glow(hs["ledger"][0], GREEN_M)], 0.7),
            "so ledger answers",
            (lambda: [hop("ledger", "router2", GREEN_M, 0.4)], 0.4),
            (lambda: [hop("router2", "router", GREEN_M, 0.4)], 0.4),
            (lambda: [hop("router", "client", GREEN_M, 0.4)], 0.4),
            "and traceroute",
            (lambda: [FadeIn(tr[2], shift=0.1 * UP), FadeOut(probe)], 0.6),
        ])

        rule = chip("most specific line wins, and every hop costs one TTL", GREEN_M, 24).move_to([0, ST_Y, 0])
        self.steps("Every router picks the most specific line and lowers the TTL. "
                   "Traceroute reads the path from the packets that die.", [
            (lambda: [glow(tpanel, GOLD_M, 1.02), r4.animate(rate_func=there_and_back).set_color(GOLD_M)], 0.9),
            (lambda: [FadeIn(rule, shift=0.15 * UP)], 0.6),
            "Traceroute reads",
            (lambda: [*[t.animate(rate_func=there_and_back).set_color(TEAL_M) for t in tr]], 1.0),
        ])
        self.wait(0.6)
