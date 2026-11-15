from sfz import *

SAY.insert(0, (r"\b192\.168\.1\.23\b", "one ninety-two dot one sixty-eight dot one dot twenty-three"))
SAY.insert(0, (r"\b192\.168\b", "one ninety-two dot one sixty-eight"))
SAY.insert(0, (r"\b41000\b", "forty-one thousand"))
SAY.insert(0, (r"\b3417\b", "thirty-four seventeen"))

LX, LY, PHY = -5.2, 2.85, 1.75         # laptop and phone
RX, RY = -0.7, 2.3                     # home router
SX, SY = 4.8, 2.3                      # server
LANE = 0.6                             # where packet headers travel
COLX = [-4.2, 0.0, 4.2]                # table columns: inside, outside, remote
HEAD_Y, ROW_Y, STATUS_Y = -0.78, [-1.45, -2.05], -2.85
PW = 4.2                               # packet header width


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(path, color=YELLOW_M, run_time=0.7, back=False):
    a, b = (path.get_end(), path.get_start()) if back else (path.get_start(), path.get_end())
    d = Dot(radius=0.08, color=color).move_to(a).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.12))


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


def host(name, addr, color, x, y, w=2.6, h=0.9):
    r = RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1)
    r.move_to([x, y, 0])
    return VGroup(r, T(name, 24).move_to([x, y + 0.18, 0]), M(addr, 18, GREY_B).move_to([x, y - 0.2, 0]))


def lane_x(x):
    return min(max(x, -6.55 + PW / 2), 6.55 - PW / 2)


def line(prefix, addr, color=WHITE):
    return M(f"{prefix} {addr}", 19, color)


def pkt(src, dst, x, color=WHITE, scol=WHITE, dcol=WHITE):
    """A packet header: where it's from and where it's going."""
    a, b = line("from", src, scol), line("to  ", dst, dcol)
    r = RoundedRectangle(corner_radius=0.1, width=PW, height=0.95, stroke_color=color, stroke_width=2.5).set_fill(fillc(color), 1)
    r.move_to([lane_x(x), LANE, 0])
    a.move_to([r.get_left()[0] + 0.22 + a.width / 2, LANE + 0.2, 0])
    b.move_to([r.get_left()[0] + 0.22 + b.width / 2, LANE - 0.2, 0])
    return VGroup(r, a, b)


def reline(p, k, prefix, addr, color):
    """The k-th line of packet p rewritten (1: from, 2: to)."""
    n = line(prefix, addr, color)
    return n.move_to([p[0].get_left()[0] + 0.22 + n.width / 2, p[k].get_center()[1], 0])


def cell(s, col, row, color=WHITE, mono=True):
    return (M(s, 20, color) if mono else T(s, 22, color)).move_to([COLX[col], ROW_Y[row], 0])


def status(s, color=GREY_B):
    return T(s, 24, color).move_to([0, STATUS_Y, 0])


class Nat(Base):
    """net-03, sections 2 and 3: a laptop at 192.168.1.23 connects to 198.51.100.20:443. A private source can't be answered,
    so the home router rewrites the source to its public 203.0.113.7 and keeps an entry; the reply is mapped back. A phone
    also using port 41000 forces a port rewrite (3417, as in the lab). An unsolicited packet matches no entry; an idle
    entry expires and the laptop's next packet is dropped."""

    def construct(self):
        self.title_card("NAT: many private addresses behind one public one", "a translation table, and what it can't do")

        laptop = host("laptop", "192.168.1.23", BLUE_M, LX, LY)
        phone = host("phone", "192.168.1.24", TEAL_M, LX, PHY)
        rbox = RoundedRectangle(corner_radius=0.14, width=2.8, height=2.0, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1)
        rbox.move_to([RX, RY, 0])
        rtitle = T("home router", 24).move_to([RX, RY + 0.55, 0])
        rin = T("inside: 192.168.1.1", 18, GREY_B).move_to([RX, RY + 0.05, 0])
        rpub = T("public: 203.0.113.7", 18, GREY_B).move_to([RX, RY - 0.45, 0])
        router = VGroup(rbox, rtitle, rin, rpub)
        server = host("server", "198.51.100.20", GREEN_M, SX, SY, w=3.0, h=1.0)
        wl = Line([LX + 1.3, LY, 0], [RX - 1.4, LY, 0], stroke_width=3, color=GREY_D)
        wp = Line([LX + 1.3, PHY, 0], [RX - 1.4, PHY, 0], stroke_width=3, color=GREY_D)
        ws = Line([RX + 1.4, SY, 0], [SX - 1.5, SY, 0], stroke_width=3, color=GREY_D)
        p = pkt("192.168.1.23:41000", "198.51.100.20:443", LX)
        self.steps("A laptop at home has the address 192.168.1.23. It opens a connection to a server on the internet. "
                   "Where does the reply go?", [
            (lambda: [FadeIn(laptop)], 0.6),
            "It opens",
            (lambda: [FadeIn(router), Create(wl), Create(ws), FadeIn(server)], 0.9),
            (lambda: [FadeIn(p, shift=0.15 * DOWN)], 0.5),
            "Where does",
            (lambda: [glow(laptop[0], BLUE_M, 1.05)], 0.8),
        ])

        reply = pkt("198.51.100.20:443", "192.168.1.23:41000", SX, GREEN_M, dcol=RED_M)
        xr = tick(False, 0.22).move_to([RX + 2.45, LANE + 0.75, 0])
        st1 = status("192.168.x.x is private: no router on the internet carries packets to it", RED_M)
        self.steps("Nowhere. Addresses that start with 192.168 are private. "
                   "Millions of homes reuse them, so no router on the internet carries packets to one.", [
            (lambda: [flow(wl, BLUE_M, 0.5), p.animate.move_to([lane_x(RX), LANE, 0])], 0.6),
            (lambda: [flow(ws, BLUE_M, 0.6), p.animate.move_to([lane_x(SX), LANE, 0])], 0.7),
            (lambda: [FadeOut(p), FadeIn(reply)], 0.4),
            "Millions",
            (lambda: [reply.animate.move_to([lane_x(RX + 2.9), LANE, 0])], 1.0),
            (lambda: [Create(xr)], 0.4),
            "so no router",
            (lambda: [FadeIn(st1, shift=0.1 * UP)], 0.6),
        ])

        p2 = pkt("192.168.1.23:41000", "198.51.100.20:443", LX)
        self.steps("So the home router owns one public address. As the packet leaves, "
                   "the router rewrites its source to that address.", [
            (lambda: [FadeOut(reply), FadeOut(xr), FadeOut(st1)], 0.5),
            (lambda: [rpub.animate.set_color(GOLD_M), glow(rbox, GOLD_M, 1.04)], 0.8),
            "As the packet",
            (lambda: [FadeIn(p2, shift=0.15 * DOWN)], 0.4),
            (lambda: [flow(wl, BLUE_M, 0.5), p2.animate.move_to([lane_x(RX), LANE, 0])], 0.6),
            "rewrites its source",
            (lambda: [Transform(p2[1], reline(p2, 1, "from", "203.0.113.7:41000", GOLD_M))], 0.7),
            (lambda: [flow(ws, GOLD_M, 0.6), p2.animate.move_to([lane_x(SX), LANE, 0])], 0.7),
        ])

        ttl = T("the router's translation table", 22, GREY_B)
        ttl.move_to([-6.3 + ttl.width / 2, -0.22, 0])
        heads = VGroup(*[T(s, 22, GREY_B).move_to([COLX[i], HEAD_Y, 0]) for i, s in enumerate(("inside", "outside", "remote"))])
        rule = Line([-6.3, HEAD_Y - 0.3, 0], [6.3, HEAD_Y - 0.3, 0], stroke_width=1.5, color=GREY_D)
        row1 = VGroup(cell("192.168.1.23:41000", 0, 0, BLUE_M), cell("203.0.113.7:41000", 1, 0, GOLD_M),
                      cell("198.51.100.20:443", 2, 0))
        self.steps("Then it writes down what it did: the inside address and port, "
                   "the outside address and port, and the remote end.", [
            (lambda: [FadeOut(p2), FadeIn(ttl), FadeIn(heads), Create(rule)], 0.8),
            "the inside",
            (lambda: [FadeIn(row1[0], shift=0.1 * DOWN)], 0.5),
            "the outside",
            (lambda: [FadeIn(row1[1], shift=0.1 * DOWN)], 0.5),
            "and the remote",
            (lambda: [FadeIn(row1[2], shift=0.1 * DOWN)], 0.5),
        ])

        rp = pkt("198.51.100.20:443", "203.0.113.7:41000", SX, GREEN_M, dcol=GOLD_M)
        self.steps("The server replies to the router's address. "
                   "The router finds the entry and rewrites the destination back to the laptop.", [
            (lambda: [FadeIn(rp, shift=0.15 * DOWN)], 0.4),
            (lambda: [flow(ws, GREEN_M, 0.6, back=True), rp.animate.move_to([lane_x(RX), LANE, 0])], 0.8),
            "The router finds",
            (lambda: [Indicate(row1, color=YELLOW_M, scale_factor=1.06)], 0.8),
            "rewrites the destination",
            (lambda: [Transform(rp[2], reline(rp, 2, "to  ", "192.168.1.23:41000", BLUE_M))], 0.7),
            (lambda: [flow(wl, GREEN_M, 0.5, back=True), rp.animate.move_to([lane_x(LX), LANE, 0])], 0.7),
            (lambda: [glow(laptop[0], GREEN_M, 1.05)], 0.6),
        ])

        pp = pkt("192.168.1.24:41000", "198.51.100.20:443", LX)
        row2 = VGroup(cell("192.168.1.24:41000", 0, 1, TEAL_M), cell("203.0.113.7:41000", 1, 1, RED_M),
                      cell("198.51.100.20:443", 2, 1))
        clash = status("two connections, one identical header: whose reply is it?", RED_M)
        self.steps("Now the phone also connects from port 41000 to the same server. "
                   "Rewrite only the address, and its packets look exactly like the laptop's.", [
            (lambda: [FadeOut(rp), FadeIn(phone), Create(wp)], 0.7),
            (lambda: [FadeIn(pp, shift=0.15 * DOWN)], 0.4),
            (lambda: [flow(wp, TEAL_M, 0.5), pp.animate.move_to([lane_x(RX), LANE, 0])], 0.6),
            "Rewrite only",
            (lambda: [Transform(pp[1], reline(pp, 1, "from", "203.0.113.7:41000", RED_M))], 0.6),
            (lambda: [FadeIn(row2, shift=0.1 * DOWN)], 0.5),
            "look exactly",
            (lambda: [Indicate(row1[1], color=RED_M), Indicate(row2[1], color=RED_M), FadeIn(clash, shift=0.1 * UP)], 0.9),
        ])

        new_out = cell("203.0.113.7:3417", 1, 1, GOLD_M)
        self.steps("So the router rewrites the port too. "
                   "The phone's connection leaves from port 3417 and gets its own entry.", [
            (lambda: [FadeOut(clash)], 0.4),
            "rewrites the port",
            (lambda: [Transform(pp[1], reline(pp, 1, "from", "203.0.113.7:3417", GOLD_M))], 0.7),
            "and gets its own",
            (lambda: [Transform(row2[1], new_out)], 0.6),
            (lambda: [flow(ws, GOLD_M, 0.6), pp.animate.move_to([lane_x(SX), LANE, 0])], 0.7),
        ])

        st2 = status("one public address, many devices: the port tells them apart", GREEN_M)
        self.steps("Each reply is matched by its port: 41000 goes to the laptop, 3417 to the phone. "
                   "That's how thousands of devices share one address.", [
            (lambda: [FadeOut(pp)], 0.3),
            (lambda: [flow(ws, BLUE_M, 0.6, back=True)], 0.6),
            (lambda: [Indicate(row1, color=BLUE_M, scale_factor=1.06), flow(wl, BLUE_M, 0.6, back=True)], 0.8),
            "3417",
            (lambda: [flow(ws, TEAL_M, 0.6, back=True)], 0.6),
            (lambda: [Indicate(row2, color=TEAL_M, scale_factor=1.06), flow(wp, TEAL_M, 0.6, back=True)], 0.8),
            "That's how",
            (lambda: [FadeIn(st2, shift=0.1 * UP)], 0.6),
        ])

        un = pkt("198.51.100.66:51000", "203.0.113.7:5000", SX, RED_M, dcol=RED_M)
        xu = tick(False, 0.24).move_to([lane_x(RX) + PW / 2 + 0.35, LANE, 0])
        st3 = status("no entry for port 5000: the router can't know which device, so it drops it", RED_M)
        self.steps("Now a packet arrives from outside that nobody inside asked for. No entry matches, "
                   "so the router doesn't know which device it's for, and drops it.", [
            (lambda: [FadeOut(st2), FadeIn(un, shift=0.15 * DOWN)], 0.5),
            (lambda: [flow(ws, RED_M, 0.6, back=True), un.animate.move_to([lane_x(RX), LANE, 0])], 0.8),
            "No entry matches",
            (lambda: [Indicate(row1[1], color=RED_M), Indicate(row2[1], color=RED_M)], 0.8),
            "so the router",
            (lambda: [Create(xu), FadeIn(st3, shift=0.1 * UP)], 0.7),
            "and drops it",
            (lambda: [FadeOut(un, scale=0.7), FadeOut(xu)], 0.6),
        ])

        st4 = status("to let traffic in: a port forward, or a load balancer with a public address", GOLD_M)
        self.steps("Letting traffic in takes a port forward set up by hand, or a load balancer with its own public address.", [
            (lambda: [Transform(st3, st4)], 0.8),
            (lambda: [glow(rbox, GOLD_M, 1.04)], 0.9),
        ])

        idle = status("the laptop's connection: idle for 0 s")
        idle2 = status("the laptop's connection: idle for 5 minutes", RED_M)
        strike = Line([COLX[0] - 1.6, ROW_Y[0], 0], [COLX[2] + 1.6, ROW_Y[0], 0], stroke_width=3, color=RED_M)
        self.steps("Entries also expire. When a connection sits idle too long, "
                   "the router deletes its entry, and tells neither end.", [
            (lambda: [FadeOut(st3)], 0.4),
            "When a connection",
            (lambda: [FadeIn(idle)], 0.4),
            (lambda: [Transform(idle, idle2)], 1.0),
            "the router deletes",
            (lambda: [Create(strike)], 0.5),
            (lambda: [FadeOut(VGroup(row1, strike, idle))], 0.6),
            "and tells neither",
            (lambda: [glow(laptop[0], GREY_B, 1.04), glow(server[0], GREY_B, 1.04)], 0.8),
        ])

        lp = pkt("192.168.1.23:41000", "198.51.100.20:443", LX)
        xl = tick(False, 0.24).move_to([lane_x(RX) + PW / 2 + 0.35, LANE, 0])
        st5 = status("no entry: dropped or reset, on a connection both ends think is open", RED_M)
        self.steps("The laptop's next packet on it matches nothing, and is dropped or reset. "
                   "That's the reset on a pooled connection that worked minutes ago.", [
            (lambda: [FadeIn(lp, shift=0.15 * DOWN)], 0.4),
            (lambda: [flow(wl, BLUE_M, 0.5), lp.animate.move_to([lane_x(RX), LANE, 0])], 0.7),
            "matches nothing",
            (lambda: [Create(xl), lp[0].animate.set_stroke(RED_M)], 0.5),
            "That's the reset",
            (lambda: [FadeIn(st5, shift=0.1 * UP)], 0.7),
        ])

        self.steps("NAT works because the router remembers every conversation. "
                   "A packet it has no memory of has nowhere to go.", [
            (lambda: [FadeOut(lp), FadeOut(xl), Indicate(row2, color=GOLD_M, scale_factor=1.06)], 1.0),
            "A packet",
            (lambda: [glow(rbox, WHITE, 1.04)], 1.0),
        ])
        self.wait(0.6)
