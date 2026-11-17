from sfz import *

SAY.insert(0, (r"\bMAC\b", "mac"))
SAY.insert(0, (r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b", r"\1 dot \2 dot \3 dot \4"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
TOP_Y, BW, BH = 2.15, 3.0, 1.25          # the three computers
CL_X, RT_X, PR_X = -4.6, 0.0, 4.6
SW_Y, SW_W, SW_H = -0.15, 2.4, 0.7       # the switch
CARD_Y, CARD_W, CARD_H = -1.5, 3.95, 1.0 # ARP caches under client and peer
PAN_Y, PAN_W, PAN_H = -1.6, 4.65, 1.3    # the frame on the wire
TAG_Y = TOP_Y + BH / 2 + 0.33
CAP_Y, BAR_Y = -2.88, -3.38
MAC_CL, MAC_PR = "ee:02:07:41:4d:8c", "4a:9d:40:b1:a5:9e"


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


# ---- wires and frames moving on them ----
def to_sw(x):
    """From a computer's bottom edge, down its wire, to the middle of the switch."""
    top = TOP_Y - BH / 2
    return [[x, top, 0], [x, SW_Y, 0], [0, SW_Y, 0]] if x else [[0, top, 0], [0, SW_Y, 0]]


def route(a, b):
    return to_sw(a) + list(reversed(to_sw(b)))[1:]


def run(pts, color=YELLOW_M, rt=1.0):
    """A dot (a frame) running along a wire. It passes under the switch's box."""
    d = Dot(radius=0.09, color=color).move_to(pts[0]).set_z_index(-2)
    path = VMobject().set_points_as_corners(pts)
    return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, path, rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.12))


def wire(x):
    pts = to_sw(x)
    if x:
        pts[-1] = [np.sign(x) * SW_W / 2, SW_Y, 0]
    else:
        pts[-1] = [0, SW_Y + SW_H / 2, 0]
    return VMobject(stroke_color=GREY_B, stroke_width=2.5).set_points_as_corners(pts).set_z_index(-5)


# ---- the pieces ----
def computer(name, ip, mac, x):
    r = RoundedRectangle(corner_radius=0.14, width=BW, height=BH, stroke_color=WHITE, stroke_width=3).set_fill(BLACK, 1)
    r.move_to([x, TOP_Y, 0])
    if mac:
        parts = [T(name, 24).move_to([x, TOP_Y + 0.36, 0]), M(ip, 18).move_to([x, TOP_Y - 0.03, 0]),
                 M(mac, 15, GREY_B).move_to([x, TOP_Y - 0.36, 0])]
    else:
        parts = [T(name, 24).move_to([x, TOP_Y + 0.2, 0]), M(ip, 18).move_to([x, TOP_Y - 0.2, 0])]
    return VGroup(r, *parts)


def switch_box():
    r = RoundedRectangle(corner_radius=0.12, width=SW_W, height=SW_H, stroke_color=GREY_B, stroke_width=3).set_fill(BLACK, 1)
    r.move_to([0, SW_Y, 0])
    ports = VGroup(T("port 1", 16, GREY_C).move_to([-SW_W / 2 - 0.62, SW_Y + 0.2, 0]),
                   T("port 2", 16, GREY_C).move_to([0.5, SW_Y + SW_H / 2 + 0.3, 0]),
                   T("port 3", 16, GREY_C).move_to([SW_W / 2 + 0.62, SW_Y + 0.2, 0]))
    return VGroup(r, T("switch", 22).move_to(r), ports)


def card(x, title, color=GREY_B):
    r = RoundedRectangle(corner_radius=0.1, width=CARD_W, height=CARD_H, stroke_color=color, stroke_width=2).set_fill("#0c0c0c", 1)
    r.move_to([x, CARD_Y, 0])
    return VGroup(r, left_at(T(title, 18, GREY_B), x - CARD_W / 2 + 0.2, CARD_Y + 0.26))


def crow(x, s, color=WHITE, mono=True):
    t = M(s, 14, color) if mono else T(s, 18, color)
    return left_at(t, x - CARD_W / 2 + 0.18, CARD_Y - 0.17)


def panel(lines, color):
    r = RoundedRectangle(corner_radius=0.12, width=PAN_W, height=PAN_H, stroke_color=color, stroke_width=3)
    r.set_fill(fillc(color, 0.12), 1).move_to([0, PAN_Y, 0])
    body = VGroup(*lines).arrange(DOWN, buff=0.15).move_to(r)
    return VGroup(r, body)


def mark_q(x):
    return T("?", 32, YELLOW_M).move_to([x + BW / 2 + 0.25, TOP_Y + 0.3, 0])


class Arp(Base):
    """net-02, section 2. Client (10.10.1.10) wants to ping peer (10.10.1.20) on its own link but has no MAC for it. No
    list can stay right (the switch never reads IP addresses; a file goes out of date). Like a barista calling "flat
    white for Sam!", client broadcasts "who has 10.10.1.20? tell 10.10.1.10"; peer stores client and answers to client
    alone; client caches the answer. ARP trusts any answer and reaches one link only."""

    def set_pan(self, lines, color):
        new = panel(lines, color)
        old, self.pan = self.pan, new
        return [swap(old, new)]

    def unpan(self):
        old, self.pan = self.pan, None
        return [FadeOut(old)] if old is not None else []

    def set_row(self, which, new):
        old = self.rows[which]
        self.rows[which] = new
        return [swap(old, new, RIGHT)]

    def construct(self):
        self.capm = self.pan = None
        self.rows = {"cl": None, "pr": None}
        self.title_card("Who has 10.10.1.20?", "how a computer finds a neighbour's card by asking the room")

        # ---------------- scene 1: the missing name ----------------
        cl = computer("client", "10.10.1.10", MAC_CL, CL_X)
        rt = computer("router", "10.10.1.2", None, RT_X)
        pr = computer("peer", "10.10.1.20", MAC_PR, PR_X)
        sw = switch_box()
        wires = VGroup(wire(CL_X), wire(RT_X), wire(PR_X))
        self.steps("Three computers share one link, plugged into a switch, the box that joins their cables.", [
            (lambda: [LaggedStart(*[FadeIn(c, shift=0.15 * DOWN) for c in (cl, rt, pr)], lag_ratio=0.25)], 1.2),
            "plugged into",
            (lambda: [FadeIn(sw[:2]), Create(wires)], 0.9),
            (lambda: [FadeIn(sw[2])], 0.4),
        ])
        self.steps("Client wants to ping peer, at 10.10.1.20. A ping is a small test message: are you there?", [
            (lambda: [glow(cl[0], WHITE)], 0.6),
            "at 10.10",
            (lambda: [Indicate(pr[2], color=YELLOW_M, scale_factor=1.1)], 0.8),
            "A ping is",
            (lambda: self.cap("ping: a small test message that asks \"are you there?\""), 0.5),
        ])
        self.steps("Every network card has a name, its MAC address: six bytes, like this one. And every frame, each chunk of "
                   "data sent across the link, must carry the MAC of the card it's for.", [
            "its MAC address",
            (lambda: [Indicate(cl[3], color=YELLOW_M, scale_factor=1.12), *self.cap("MAC address: the network card's name, six bytes")], 0.9),
            "And every frame",
            (lambda: [*self.uncap(), *self.set_pan([M("to ??:??:??:??:??:??", 17, RED_M), T("ping 10.10.1.20: are you there?", 20)], GREY_B)], 0.7),
            "the card it's for",
            (lambda: [Indicate(self.pan[1][0], color=RED_M, scale_factor=1.08)], 0.7),
        ])
        qm = T("?", 48, YELLOW_M).move_to([PAN_W / 2 + 0.45, PAN_Y, 0])
        self.steps("Client knows peer's IP address. But peer's MAC? Nothing has told it. So where does client get it?", [
            (lambda: [Indicate(pr[2], color=WHITE, scale_factor=1.1)], 0.7),
            "But peer's MAC",
            (lambda: [Indicate(pr[3], color=RED_M, scale_factor=1.12)], 0.7),
            "So where",
            (lambda: [FadeIn(qm, scale=0.6)], 0.5),
        ])

        # ---------------- scene 2: a list somewhere? ----------------
        self.steps("The tempting answer is a list. Surely something keeps every card's address. The switch, perhaps?", [
            (lambda: [FadeOut(qm)], 0.3),
            "The switch",
            (lambda: [glow(sw[0], YELLOW_M, 1.05)], 0.8),
        ])
        self.steps("But a switch knows only MAC addresses, and which port each one sits behind. It never reads an IP address.", [
            "which port",
            (lambda: [LaggedStart(*[Indicate(p, color=WHITE, scale_factor=1.15) for p in sw[2]], lag_ratio=0.25)], 1.0),
            "It never reads",
            (lambda: self.cap("a switch knows MACs and ports. It never reads an IP address."), 0.5),
        ])
        file_c = card(CL_X, "a file of neighbours")
        file_r = crow(CL_X, "10.10.1.20 → last week's card", WHITE, mono=False)
        strikes = VGroup()
        self.steps("Then give every computer a file of its neighbours. It breaks the first time anything changes.", [
            (lambda: [*self.uncap(), FadeIn(file_c, shift=0.1 * UP)], 0.6),
            (lambda: [FadeIn(file_r)], 0.4),
            "It breaks",
            (lambda: [glow(file_c[0], RED_M, 1.03)], 0.7),
        ])
        self.steps("A broken card gets replaced. Tomorrow, 10.10.1.20 goes to a different laptop. And Docker, which runs these "
                   "little lab computers, gives each one a new random MAC every time it starts.", [
            (lambda: self.cap("a broken card gets replaced"), 0.4),
            "Tomorrow",
            (lambda: self.cap("10.10.1.20 goes to a different laptop"), 0.4),
            "And Docker",
            (lambda: self.cap("Docker gives each lab computer a new random MAC at every start"), 0.4),
            "a new random",
            (lambda: [Indicate(pr[3], color=RED_M, scale_factor=1.12), Indicate(cl[3], color=RED_M, scale_factor=1.12)], 0.8),
        ])
        strike = Line(file_r.get_left() + 0.08 * LEFT, file_r.get_right() + 0.08 * RIGHT, stroke_width=3, color=RED_M)
        self.steps("Nobody could keep that file right.", [
            (lambda: [Create(strike), file_r.animate.set_color(RED_M), file_c[0].animate.set_stroke(RED_M), *self.cap("out of date", RED_M)], 0.7),
        ])

        # ---------------- scene 3: the barista ----------------
        tags = [T("the barista", 20, GREY_B).move_to([CL_X, TAG_Y, 0]), T("another customer", 20, GREY_B).move_to([RT_X, TAG_Y, 0]),
                T("Sam", 20, GREY_B).move_to([PR_X, TAG_Y, 0])]
        self.steps("So let's borrow a trick from a café at lunchtime. The barista calls out, \"Flat white for Sam!\" Everyone hears it.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(file_c, file_r, strike)), *self.unpan()], 0.6),
            "The barista",
            (lambda: [FadeIn(tags[0], shift=0.1 * DOWN)], 0.5),
            "Flat white",
            (lambda: self.cap("\"Flat white for Sam!\"", WHITE, 28), 0.5),
            "Everyone hears",
            (lambda: [run(to_sw(CL_X), YELLOW_M, 0.7)], 0.7),
            (lambda: [run(list(reversed(to_sw(RT_X))), YELLOW_M, 0.6), run(list(reversed(to_sw(PR_X))), YELLOW_M, 0.6),
                      FadeIn(tags[1], shift=0.1 * DOWN)], 0.6),
        ])
        self.steps("One person stands up and gets the cup. Next time, she'll remember Sam.", [
            (lambda: [FadeIn(tags[2], shift=0.1 * DOWN), glow(pr[0], WHITE)], 0.7),
            "gets the cup",
            (lambda: [run(route(PR_X, CL_X), WHITE, 1.1)], 1.1),
            "remember Sam",
            (lambda: [Indicate(tags[2], color=WHITE, scale_factor=1.2)], 0.7),
        ])
        self.steps("Notice what she doesn't do: keep a photo album of every customer's face. It would be out of date by Tuesday.", [
            "a photo album",
            (lambda: self.cap("no photo album of faces: it would be out of date by Tuesday"), 0.5),
        ])
        self.steps("Let's map it. The barista is client. Sam's name is the IP address, and Sam's face is the MAC.", [
            (lambda: [*self.uncap()], 0.3),
            "The barista is",
            (lambda: [Indicate(tags[0], color=WHITE, scale_factor=1.15), glow(cl[0], WHITE)], 0.7),
            "Sam's name",
            (lambda: [Indicate(pr[2], color=YELLOW_M, scale_factor=1.12), *self.cap("Sam's name = the IP address")], 0.7),
            "Sam's face",
            (lambda: [Indicate(pr[3], color=YELLOW_M, scale_factor=1.12), *self.cap("Sam's face = the MAC")], 0.7),
        ])
        self.steps("Calling to the whole room is a broadcast: a frame to an address that every card accepts. "
                   "And remembering Sam is a cache.", [
            (lambda: self.cap("calling to the whole room = a broadcast, to ff:ff:ff:ff:ff:ff"), 0.5),
            (lambda: [run(to_sw(CL_X), YELLOW_M, 0.6)], 0.6),
            (lambda: [run(list(reversed(to_sw(RT_X))), YELLOW_M, 0.5), run(list(reversed(to_sw(PR_X))), YELLOW_M, 0.5)], 0.5),
            "remembering Sam",
            (lambda: self.cap("remembering Sam = a cache: a short list of recent answers"), 0.5),
        ])

        # ---------------- scene 4: ask the room ----------------
        cc = card(CL_X, "ARP cache")
        pc = card(PR_X, "ARP cache")
        empty_c, empty_p = crow(CL_X, "empty", GREY_C, mono=False), crow(PR_X, "empty", GREY_C, mono=False)
        q_lines = lambda: [M("to ff:ff:ff:ff:ff:ff", 17, YELLOW_M), T("who has 10.10.1.20?  tell 10.10.1.10", 20),
                           M("target MAC 00:00:00:00:00:00", 14, GREY_B)]
        self.steps("So client asks. It broadcasts one question: who has 10.10.1.20? Tell 10.10.1.10.", [
            (lambda: [*self.uncap(), FadeIn(VGroup(cc, pc)), FadeIn(empty_c), FadeIn(empty_p)], 0.6),
            "It broadcasts",
            (lambda: self.set_pan(q_lines(), YELLOW_M), 0.7),
            "who has",
            (lambda: [Indicate(self.pan[1][1], color=YELLOW_M, scale_factor=1.06)], 0.8),
        ])
        self.rows = {"cl": empty_c, "pr": empty_p}
        self.steps("Inside, the target's MAC is all zeros. That empty field is the question.", [
            "all zeros",
            (lambda: [Indicate(self.pan[1][2], color=YELLOW_M, scale_factor=1.12)], 0.8),
        ])
        qs = [mark_q(RT_X), mark_q(PR_X)]
        self.steps("Who will hear it, and who will answer? Pause and guess.", [
            (lambda: [LaggedStart(*[FadeIn(q, scale=0.5) for q in qs], lag_ratio=0.3)], 0.7),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        notme = T("not me", 18, GREY_B).move_to([RT_X + BW / 2 + 0.5, TOP_Y - 0.1, 0])
        self.steps("The switch sends a broadcast out of every port, so everyone hears it. Router isn't 10.10.1.20, "
                   "and it has never met client, so it drops the question.", [
            (lambda: [*self.uncap(), *[FadeOut(q) for q in qs]], 0.3),
            (lambda: [run(to_sw(CL_X), YELLOW_M, 0.7)], 0.7),
            (lambda: [run(list(reversed(to_sw(RT_X))), YELLOW_M, 0.6), run(list(reversed(to_sw(PR_X))), YELLOW_M, 0.6)], 0.6),
            "Router isn't",
            (lambda: [rt.animate.set_opacity(0.35), FadeIn(notme)], 0.6),
            "drops the question",
            (lambda: [Indicate(notme, color=WHITE)], 0.6),
        ])
        a_lines = lambda: [M(f"to {MAC_CL}", 17), M(f"10.10.1.20 is at {MAC_PR}", 15, GREEN_M)]
        self.steps("Peer is 10.10.1.20. It writes client down, and answers: 10.10.1.20 is at this card.", [
            (lambda: [glow(pr[0], WHITE)], 0.6),
            "It writes client",
            (lambda: [*self.set_row("pr", crow(PR_X, f"10.10.1.10 → {MAC_CL}", GREEN_M)), glow(pc[0], GREEN_M)], 0.8),
            "and answers",
            (lambda: self.set_pan(a_lines(), WHITE), 0.7),
        ])
        self.steps("The answer goes to client's card alone. The switch learned client's port from the question, "
                   "so router never even hears it. Only the question needed the whole room.", [
            (lambda: [run(route(PR_X, CL_X), WHITE, 1.2)], 1.2),
            "The switch learned",
            (lambda: [Indicate(sw[2][0], color=WHITE, scale_factor=1.2)], 0.7),
            "router never",
            (lambda: [Indicate(notme, color=WHITE)], 0.6),
            "Only the question",
            (lambda: self.cap("the question goes to everyone; the answer goes to the asker alone", WHITE), 0.5),
        ])

        # ---------------- scene 5: the name, and the memory ----------------
        self.steps("This is ARP, the Address Resolution Protocol. It turns an IP address into a MAC, and it has done that job since 1982.", [
            "This is ARP",
            (lambda: self.cap("ARP, the Address Resolution Protocol: an IP address in, a MAC out", WHITE), 0.6),
            "since 1982",
            (lambda: self.cap("written down in 1982 (RFC 826), and still doing this job"), 0.5),
        ])
        p_lines = lambda: [M(f"to {MAC_PR}", 17), T("ping 10.10.1.20: are you there?", 20)]
        r_lines = lambda: [M(f"to {MAC_CL}", 17), T("ping reply: yes, I'm here", 20)]
        self.steps("Client keeps the answer in its ARP cache, a short list of recent answers. "
                   "Now the ping leaves at once, addressed to peer's card.", [
            (lambda: self.uncap(), 0.3),
            "Client keeps",
            (lambda: [*self.set_row("cl", crow(CL_X, f"10.10.1.20 → {MAC_PR}", GREEN_M)), glow(cc[0], GREEN_M)], 0.8),
            "Now the ping",
            (lambda: self.set_pan(p_lines(), WHITE), 0.6),
            (lambda: [run(route(CL_X, PR_X), WHITE, 1.2)], 1.2),
        ])
        self.steps("And peer answers without asking anything back. It wrote client down from the question.", [
            (lambda: self.set_pan(r_lines(), WHITE), 0.6),
            (lambda: [run(route(PR_X, CL_X), WHITE, 1.2)], 1.2),
            "It wrote client",
            (lambda: [glow(pc[0], GREEN_M)], 0.7),
        ])
        self.steps("Two ARP messages, and from now on, every frame between them goes to one card only.", [
            (lambda: [*self.cap("two ARP messages; after that, every frame goes to one card only", WHITE)], 0.5),
            (lambda: [run(route(CL_X, PR_X), WHITE, 0.9)], 0.9),
        ])

        # ---------------- scene 6: where the café breaks ----------------
        lie = lambda: [M(f"to {MAC_CL}", 17, RED_M), T("10.10.1.20 is at router's card", 20, RED_M)]
        self.steps("Here the café picture breaks. A barista might notice a stranger grabbing Sam's coffee. ARP checks nothing.", [
            (lambda: self.cap("where the café picture breaks"), 0.5),
            "ARP checks",
            (lambda: [*self.set_pan(lie(), RED_M), *self.cap("ARP checks nothing", RED_M)], 0.6),
        ])
        good_row = self.rows["cl"]
        self.steps("Any card on the link can answer for any IP address, and the asker believes it.", [
            (lambda: [rt.animate.set_opacity(1), FadeOut(notme), run(route(RT_X, CL_X), RED_M, 1.1)], 1.1),
            "the asker believes",
            (lambda: [*self.set_row("cl", crow(CL_X, "10.10.1.20 → router's card", RED_M, mono=False)), glow(cc[0], RED_M)], 0.7),
        ])
        self.steps("ARP trusts everyone: lovely in a friend, worrying in a network. The lesson's Go deeper shows what an attacker does with that.", [
            "lovely in a friend",
            (lambda: self.cap("ARP trusts everyone: lovely in a friend, worrying in a network", WHITE), 0.5),
            "The lesson's",
            (lambda: [*self.set_row("cl", crow(CL_X, f"10.10.1.20 → {MAC_PR}", GREEN_M)), *self.unpan()], 0.6),
        ])

        # ---------------- scene 7: two limits ----------------
        self.steps("Two more limits. ARP reaches one link only. For a computer on another network, client asks for the router's MAC instead.", [
            (lambda: self.cap("limit 1: one link only. For anything further, ask for the router's MAC."), 0.5),
            "asks for the router",
            (lambda: [glow(rt[0], WHITE)], 0.7),
        ])
        self.steps("And a remembered answer can go out of date, so entries are forgotten on purpose. The next section shows how.", [
            (lambda: self.cap("limit 2: answers go out of date, so the cache forgets on purpose"), 0.5),
            "forgotten on purpose",
            (lambda: [self.rows["cl"].animate.set_opacity(0.4), self.rows["pr"].animate.set_opacity(0.4)], 0.8),
            (lambda: [self.rows["cl"].animate.set_opacity(1), self.rows["pr"].animate.set_opacity(1)], 0.5),
        ])

        # ---------------- scene 8: the moral, and a check ----------------
        self.steps("So where did client get peer's MAC? It asked the room, once. Ask everyone, answer one, remember for a while.", [
            (lambda: self.cap("where did client get peer's MAC?", WHITE), 0.5),
            "It asked the room",
            (lambda: [run(to_sw(CL_X), YELLOW_M, 0.6)], 0.6),
            (lambda: [run(list(reversed(to_sw(RT_X))), YELLOW_M, 0.5), run(list(reversed(to_sw(PR_X))), YELLOW_M, 0.5)], 0.5),
            "Ask everyone",
            (lambda: self.cap("ask everyone, answer one, remember for a while", YELLOW_M, 30), 0.6),
            "remember for",
            (lambda: [glow(cc[0], GREEN_M), glow(pc[0], GREEN_M)], 0.7),
        ], after=0.5)
        self.steps("One quick check. Now peer wants to ping client. Does peer have to ask the room first? Pause and think.", [
            (lambda: self.uncap(), 0.3),
            "Now peer wants",
            (lambda: [glow(pr[0], WHITE)], 0.6),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        c_lines = lambda: [M(f"to {MAC_CL}", 17), T("ping 10.10.1.10: are you there?", 20)]
        self.steps("No. Peer wrote client down from the question. It sends straight away.", [
            (lambda: [*self.uncap(), glow(pc[0], GREEN_M)], 0.6),
            "It sends",
            (lambda: [*self.set_pan(c_lines(), WHITE)], 0.5),
            (lambda: [run(route(PR_X, CL_X), WHITE, 1.1)], 1.1),
        ], after=0.3)
        self.play(*self.cap("ask everyone, answer one, remember for a while", YELLOW_M, 30), run_time=0.6)
        self.wait(2.0)
