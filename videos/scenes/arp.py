from sfz import *

SAY.insert(0, (r"\b10\.10\.2\.20\b", "ten dot ten dot two dot twenty"))
SAY.insert(0, (r"\b10\.10\.1\.10\b", "ten dot ten dot one dot ten"))
SAY.insert(0, (r"\b10\.10\.1\.2\b", "ten dot ten dot one dot two"))

HY, HW, HH = 2.6, 2.7, 1.3               # hosts row
HX = {"client": -5.1, "peer": -1.85, "router": 1.35, "server": 5.15}
BUS_Y, BUS_X0, BUS_X1 = 1.3, -6.3, 2.0    # the lan link
CHIP_Y = 0.62                             # ARP messages
FY = -0.95                                # the frame
CX, CW = 4.72, 3.55                       # client's cache (or file)
ST_Y = -3.0
CELL_X = [-5.3, -3.33]                    # frame: to MAC, from MAC


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def run(path, color=YELLOW_M, run_time=1.0):
    """A dot that runs along a polyline and stays invisible until its turn."""
    d = Dot(radius=0.08, color=color).move_to(path.get_start()).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, path, rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.12))


def poly(*pts):
    return VMobject().set_points_as_corners([np.array([x, y, 0]) for x, y in pts])


def via_bus(a, b):
    """From host a down to the lan link, along it, and up to host b."""
    top = HY - HH / 2
    return poly((HX[a], top), (HX[a], BUS_Y), (HX[b], BUS_Y), (HX[b], top))


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


def host(name, ip, mac, color):
    x = HX[name]
    r = RoundedRectangle(corner_radius=0.14, width=HW, height=HH, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1)
    r.move_to([x, HY, 0])
    return VGroup(r, T(name, 28).move_to([x, HY + 0.36, 0]), M(ip, 22).move_to([x, HY - 0.03, 0]),
                  M(mac, 19, GREY_B).move_to([x, HY - 0.38, 0]))


def cell_val(s, k, color=WHITE):
    return M(s, 22, color).move_to([CELL_X[k], FY - 0.2, 0])


def ip_line(s, k, color=WHITE):
    return left_at(M(s, 22, color), -1.92, FY + (0.22 if k == 0 else -0.22))


def store_title(s):
    return T(s, 24, GREY_B).move_to([CX, FY + 0.38, 0])


def store_entry(s, color=WHITE):
    return M(s, 18, color).move_to([CX, FY - 0.22, 0])


def status(s, color=GREY_B):
    return T(s, 28, color).move_to([0, ST_Y, 0])


def msg(s, color):
    return chip(s, color, 19, mono=True).move_to([(BUS_X0 + BUS_X1) / 2, CHIP_Y, 0])


class Arp(Base):
    """net-02, section 2: client (10.10.1.10) sends to a server at 10.10.2.20 through router 10.10.1.2. It knows the
    router's IP, not its MAC. A file of neighbours goes stale when a card is replaced. ARP broadcasts who-has, the router
    answers by unicast, client caches it. The frame carries the next hop's MAC while the IP header keeps the final
    destination; the router rewraps the same packet in a new frame for the wan link."""

    def construct(self):
        self.title_card("ARP: who has this IP?", "from the IP address you know to the MAC a frame needs")

        cl = host("client", "10.10.1.10", "ee:02..8c", BLUE_M)
        pe = host("peer", "10.10.1.20", "4a:9d..9e", GREY_B)
        ro = host("router", "10.10.1.2", "a6:c2..aa", GOLD_M)
        sv = host("server", "10.10.2.20", "72:0e..41", GREEN_M)
        bus = Line([BUS_X0, BUS_Y, 0], [BUS_X1, BUS_Y, 0], stroke_width=3, color=GREY_C)
        drops = VGroup(*[Line([HX[n], HY - HH / 2, 0], [HX[n], BUS_Y, 0], stroke_width=3, color=GREY_C)
                         for n in ("client", "peer", "router")])
        lan = T("lan", 24, GREY_B).move_to([BUS_X1 + 0.38, BUS_Y, 0])
        wan = Line([HX["router"] + HW / 2, HY, 0], [HX["server"] - HW / 2, HY, 0], stroke_width=3, color=GREY_C)
        wanl = T("wan", 24, GREY_B).move_to([(HX["router"] + HX["server"]) / 2, HY + 0.32, 0])

        inner = RoundedRectangle(corner_radius=0.1, width=4.6, height=1.15, stroke_color=BLUE_M, stroke_width=2.5)
        inner.set_fill(fillc(BLUE_M), 1).move_to([0.15, FY, 0])
        ipf = ip_line("from 10.10.1.10", 0)
        ipt = ip_line("to   10.10.2.20", 1)
        ipl = T("IP packet", 22, GREY_B).move_to([1.75, FY, 0])
        self.steps("Client wants to send a payment request to a server at 10.10.2.20, on another network. "
                   "Its routing table says the way there is through the router, at 10.10.1.2.", [
            (lambda: [FadeIn(cl), FadeIn(sv)], 0.7),
            (lambda: [FadeIn(inner), FadeIn(ipf), FadeIn(ipt), FadeIn(ipl)], 0.8),
            "Its routing table",
            (lambda: [Create(bus), Create(drops), FadeIn(lan), FadeIn(pe), FadeIn(ro), Create(wan), FadeIn(wanl)], 1.2),
            "through the router",
            (lambda: [glow(ro[0], GOLD_M)], 0.8),
        ])

        outer = RoundedRectangle(corner_radius=0.12, width=8.9, height=1.55, stroke_color=WHITE, stroke_width=2.5)
        outer.set_fill(BLACK, 1).move_to([-1.85, FY, 0]).set_z_index(-1)
        seps = VGroup(*[Line([x, FY - 0.62, 0], [x, FY + 0.62, 0], stroke_width=1.5, color=GREY_D) for x in (-4.3, -2.35)])
        heads = VGroup(T("to MAC", 22, GREY_B).move_to([CELL_X[0], FY + 0.3, 0]),
                       T("from MAC", 22, GREY_B).move_to([CELL_X[1], FY + 0.3, 0]))
        to_v = cell_val("?", 0, RED_M)
        from_v = cell_val("ee:02..8c", 1)
        flab = left_at(T("frame on the lan link", 22, GREY_B), -6.3, FY - 1.05)
        self.steps("But a network card sends frames, and a frame is addressed to a card, by its MAC address. "
                   "Client knows the router's IP address. It doesn't know its MAC.", [
            (lambda: [FadeIn(outer), FadeIn(seps), FadeIn(heads), FadeIn(flab)], 0.9),
            "by its MAC",
            (lambda: [FadeIn(from_v), cl[3].animate.set_color(BLUE_M)], 0.6),
            "Client knows",
            (lambda: [glow(ro[0], GOLD_M), ro[2].animate.set_color(GOLD_M)], 0.8),
            "It doesn't know",
            (lambda: [FadeIn(to_v, scale=1.3)], 0.6),
        ])

        box = RoundedRectangle(corner_radius=0.12, width=CW, height=1.55, stroke_color=GREY_B, stroke_width=2.5)
        box.set_fill(BLACK, 1).move_to([CX, FY, 0])
        ftitle = store_title("a file of neighbours")
        fent = store_entry("10.10.1.2 → 3e:91..2c")
        self.steps("The simplest fix is a file on every machine that lists each neighbour's IP and MAC.", [
            (lambda: [FadeIn(box), FadeIn(ftitle)], 0.6),
            (lambda: [FadeIn(fent, shift=0.1 * DOWN)], 0.6),
            (lambda: [Transform(to_v, cell_val("3e:91..2c", 0, GREY_A))], 0.6),
        ])

        xr = tick(False, 0.2).move_to([HX["router"] + 0.4, (HY - HH / 2 + BUS_Y) / 2, 0])
        st = status("the file names a card that's gone", RED_M)
        self.steps("It breaks the first time anything changes. The router's card was replaced last week, "
                   "so the file names a card that's gone, and every card drops the frame.", [
            "The router's card",
            (lambda: [glow(ro[0], GOLD_M), ro[3].animate.set_color(GOLD_M)], 0.8),
            "so the file names",
            (lambda: [fent.animate.set_color(RED_M), to_v.animate.set_color(RED_M)], 0.6),
            "and every card",
            (lambda: [run(via_bus("client", "router"), RED_M, 1.0)], 1.0),
            (lambda: [Create(xr), FadeIn(st, shift=0.1 * UP)], 0.5),
        ])

        req = msg("to ff:ff:ff:ff:ff:ff   who has 10.10.1.2? tell 10.10.1.10", GOLD_M)
        self.steps("So client asks. It broadcasts one question to the special address every card accepts: "
                   "who has 10.10.1.2? Tell 10.10.1.10.", [
            (lambda: [FadeOut(xr), FadeOut(st), FadeOut(box), FadeOut(ftitle), FadeOut(fent),
                      Transform(to_v, cell_val("?", 0, RED_M)), ro[3].animate.set_color(GREY_B)], 0.7),
            "It broadcasts",
            (lambda: [FadeIn(req, shift=0.1 * DOWN)], 0.6),
            "who has",
            (lambda: [run(via_bus("client", "peer"), GOLD_M, 1.0), run(via_bus("client", "router"), GOLD_M, 1.4)], 1.4),
        ])

        notme = left_at(T("not mine: stays quiet", 20, GREY_B), HX["peer"] + 0.18, (HY - HH / 2 + BUS_Y) / 2)
        rep = msg("to ee:02..8c   10.10.1.2 is at a6:c2..aa", GREEN_M)
        self.steps("Every card on the link reads it. Peer isn't 10.10.1.2, so it stays quiet. "
                   "The router is, so it answers straight back to client: here is my MAC.", [
            "Peer isn't",
            (lambda: [FadeIn(notme), pe[0].animate.set_stroke(GREY_D), pe[1].animate.set_color(GREY_C)], 0.7),
            "The router is",
            (lambda: [glow(ro[0], GOLD_M)], 0.6),
            "so it answers",
            (lambda: [FadeOut(req), FadeIn(rep, shift=0.1 * UP)], 0.6),
            (lambda: [run(via_bus("router", "client"), GREEN_M, 1.2)], 1.2),
        ])

        ctitle = store_title("client's ARP cache")
        cent = store_entry("10.10.1.2 → a6:c2..aa", GREEN_M)
        cbox = box.copy().set_stroke(BLUE_M)
        st2 = status("trusted for 15 to 45 seconds, then checked again")
        self.steps("Client keeps the answer in its ARP cache, so the next packets leave at once, with no question. "
                   "Linux trusts the entry for 15 to 45 seconds, then checks again.", [
            (lambda: [FadeIn(cbox), FadeIn(ctitle)], 0.6),
            (lambda: [FadeIn(cent, shift=0.1 * DOWN)], 0.6),
            "Linux trusts",
            (lambda: [FadeOut(notme), pe[0].animate.set_stroke(GREY_B), pe[1].animate.set_color(WHITE), FadeOut(rep),
                      FadeIn(st2, shift=0.1 * UP)], 0.8),
        ])

        self.steps("Now the frame is complete. Its MAC address names the router, the next hop. "
                   "Its IP header still names the server, the final destination.", [
            (lambda: [FadeOut(st2), Transform(to_v, cell_val("a6:c2..aa", 0, GOLD_M))], 0.8),
            "Its MAC address",
            (lambda: [glow(ro[0], GOLD_M), to_v.animate(rate_func=there_and_back).scale(1.15)], 0.9),
            "Its IP header",
            (lambda: [ipt.animate.set_color(GREEN_M), glow(sv[0], GREEN_M)], 0.9),
        ])

        self.steps("The router takes the frame and unwraps the packet. 10.10.2.20 is on its other link, "
                   "so it needs the server's MAC, and it finds it with ARP too.", [
            (lambda: [run(via_bus("client", "router"), BLUE_M, 1.1)], 1.1),
            (lambda: [VGroup(outer, seps, heads, to_v, from_v).animate.set_opacity(0.25)], 0.7),
            "so it needs",
            (lambda: [run(Line(wan.get_start(), wan.get_end()), GOLD_M, 0.7)], 0.7),
            (lambda: [run(Line(wan.get_end(), wan.get_start()), GREEN_M, 0.7)], 0.7),
        ])

        self.steps("It wraps the same packet in a new frame: from its own card, to the server's card. "
                   "The IP addresses inside don't change.", [
            (lambda: [VGroup(outer, seps, heads).animate.set_opacity(1), to_v.animate.set_opacity(1),
                      from_v.animate.set_opacity(1)], 0.5),
            (lambda: [Transform(from_v, cell_val("d2:5a..19", 1, GOLD_M)), Transform(to_v, cell_val("72:0e..41", 0, GREEN_M)),
                      Transform(flab, left_at(T("frame on the wan link", 22, GREY_B), -6.3, FY - 1.05))], 0.9),
            "The IP addresses",
            (lambda: [glow(inner, GREEN_M, 1.03), ipf.animate.set_color(GREEN_M)], 0.9),
            (lambda: [run(Line(wan.get_start(), wan.get_end()), GREEN_M, 0.8)], 0.8),
        ])

        rule = chip("the MACs change at every hop, the IP destination never does", GREEN_M, 26).move_to([0, ST_Y, 0])
        self.steps("MAC addresses change at every hop, and the IP destination stays the same the whole way. "
                   "ARP is how each hop finds the next MAC.", [
            (lambda: [to_v.animate(rate_func=there_and_back).scale(1.15), from_v.animate(rate_func=there_and_back).scale(1.15)], 0.8),
            "and the IP",
            (lambda: [ipt.animate(rate_func=there_and_back).scale(1.1), FadeIn(rule, shift=0.15 * UP)], 0.9),
            "ARP is how",
            (lambda: [glow(cbox, BLUE_M, 1.03)], 0.9),
        ])
        self.wait(0.6)
