from sfz import *

SAY.insert(0, (r"(?<![\w.])\.com\b", "dot com"))
SAY.insert(0, (r"\bexample\.com\b", "example dot com"))
SAY.insert(0, (r"\bgetByName\b", "get by name"))
SAY.insert(0, (r"\bRD\b", "R D"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
PROG = np.array([-5.55, 1.6, 0])            # your program, with the stub resolver inside
PW, PH = 2.0, 1.3
RES = np.array([-0.8, 1.6, 0])              # the recursive resolver: directory enquiries
RW, RH = 2.6, 1.3
SX = 4.75                                   # the three books, stacked as a tree
SY = [2.75, 1.3, -0.15]                     # root, com, example.com
SBW, SBH = 2.9, 0.95
NC = np.array([-1.0, -1.45, 0])             # the resolver's notes (its cache)
NW, NH = 8.0, 1.8
NX0, NX1 = NC[0] - NW / 2, NC[0] + NW / 2
NROW = [-1.25, -1.7, -2.15]
ASK_Y = 2.75                                # the question and the answer, above the program
CAP_Y, BAR_Y = -3.15, -2.72

A1, A2 = "104.20.23.154", "172.66.147.243"


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


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def frame(c, w, h, color):
    return RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=3).set_fill(fillc(color), 1).move_to(c)


def chip_at(text, color, x, y, size=18):
    t = M(text, size, color)
    r = RoundedRectangle(corner_radius=0.09, width=t.width + 0.36, height=0.46, stroke_color=color, stroke_width=2.5).set_fill(BLACK, 1)
    g = VGroup(r, t.move_to(r))
    return left_at(g, x, y)


def back(ln):
    return Line(ln.get_end(), ln.get_start())


class DnsResolution(Base):
    """net-09, section 1. Your program asks one question and gets an address; three organisations were asked. The phone
    books from section 0 and directory enquiries: the stub (one call, RD) and the recursive resolver. Walking it yourself
    costs 46 + 48 + 16 ms per lookup and would send every lookup to the root. The walk: root (referral, glue), com
    (referral), hera (the answer, AA, TTL 300); the copy goes back. Notes kept for two days and five minutes; 200 s later
    one short trip. The catch: copies. Check: ten minutes later, only example.com's own servers are asked."""

    def sub(self, k, s, color=GREY_B):
        new = T(s, 17, color).move_to([SX, SY[k] - 0.2, 0])
        old, self.subs[k] = self.subs[k], new
        return [swap(old, new)]

    def set_ask(self, text, color):
        new = chip_at(text, color, -6.5, ASK_Y)
        old, self.askm = self.askm, new
        return [swap(old, new)]

    def clear_ask(self):
        old, self.askm = self.askm, None
        return [FadeOut(old)] if old is not None else []

    def construct(self):
        self.capm = self.askm = None
        self.subs = [None, None, None]
        self.title_card("Who does the asking?", "one question, three servers, and a helper that remembers")

        # ---------------- scene 1: the question ----------------
        prog = VGroup(frame(PROG, PW, PH, BLUE_M), T("your program", 20).move_to(PROG + [0, 0.25, 0]))
        self.steps("Your program wants to talk to example.com. But a packet needs a numeric address, not a name. "
                   "So the program asks: what's the address of example.com?", [
            (lambda: [FadeIn(prog)], 0.7),
            "But a packet",
            (lambda: self.cap("a packet needs a numeric address, not a name"), 0.5),
            "So the program asks",
            (lambda: [*self.uncap(), *self.set_ask("example.com ?", BLUE_M)], 0.6),
        ])
        boxes = [VGroup(frame([SX, y, 0], SBW, SBH, GOLD_M if k == 2 else WHITE),
                        T(name, 22).move_to([SX, y + 0.18, 0])) for k, (y, name) in enumerate(zip(SY, ["root", "com", "example.com"]))]
        edges = VGroup(Line([SX, SY[0] - SBH / 2, 0], [SX, SY[1] + SBH / 2, 0]), Line([SX, SY[1] - SBH / 2, 0], [SX, SY[2] + SBH / 2, 0]))
        edges.set_stroke(GREY_C, 2.5)
        bigq = T("?", 64, YELLOW_M).move_to(RES)
        self.steps("A moment later, it has two. One question, one answer. But behind it, three different organisations were asked, "
                   "and your program spoke to none of them. Who did the asking?", [
            (lambda: self.set_ask(f"{A1}, {A2}", GREEN_M), 0.7),
            "three different",
            (lambda: [LaggedStart(*[FadeIn(b, shift=0.1 * LEFT) for b in boxes], lag_ratio=0.35), Create(edges)], 1.3),
            "Who did",
            (lambda: [FadeIn(bigq, scale=0.6)], 0.6),
        ])

        # ---------------- scene 2: the books, and directory enquiries ----------------
        self.steps("In the last section, the names were phone books. The first book only says which book covers each ending, like com.", [
            (lambda: [*self.clear_ask(), FadeOut(bigq)], 0.5),
            "The first book",
            (lambda: [*self.sub(0, "the first book"), glow(boxes[0][0], WHITE, 1.04)], 0.7),
        ])
        self.steps("The com book only says which book each company keeps. Only the company's own book has the numbers.", [
            (lambda: [*self.sub(1, "the com book"), glow(boxes[1][0], WHITE, 1.04)], 0.7),
            "Only the company's",
            (lambda: [*self.sub(2, "the company's own book"), glow(boxes[2][0], GOLD_M, 1.04)], 0.7),
        ])
        res_box = frame(RES, RW, RH, TEAL_M)
        res_t = T("directory enquiries", 20).move_to(RES + [0, 0.25, 0])
        res = VGroup(res_box, res_t)
        l_pr = Line([PROG[0] + PW / 2 + 0.05, PROG[1], 0], [RES[0] - RW / 2 - 0.05, RES[1], 0], stroke_color=GREY_B, stroke_width=2.5)
        starts = [[RES[0] + RW / 2 + 0.05, RES[1] + d, 0] for d in (0.3, 0, -0.3)]
        lines = [Line(starts[k], [SX - SBW / 2 - 0.05, SY[k], 0], stroke_color=GREY_B, stroke_width=2.5) for k in range(3)]
        self.steps("You could read all three yourself. Most people don't. They ring directory enquiries: one call, and somebody else reads the books.", [
            "They ring",
            (lambda: [FadeIn(res), Create(l_pr)], 0.8),
            "one call",
            (lambda: [travel(l_pr, BLUE_M, 0.6)], 0.7),
            "somebody else",
            (lambda: [LaggedStart(*[Create(l) for l in lines], lag_ratio=0.3)], 0.9),
        ])
        stub = VGroup(RoundedRectangle(corner_radius=0.08, width=1.6, height=0.42, stroke_color=BLUE_M, stroke_width=2).set_fill(fillc(BLUE_M, 0.3), 1),
                      T("stub resolver", 17, BLUE_M)).move_to(PROG + [0, -0.25, 0])
        stub[1].move_to(stub[0])
        self.steps("Your program is the caller. Inside it is a small piece of code called the stub resolver; Java's getByName calls it.", [
            (lambda: [glow(prog[0], BLUE_M, 1.04)], 0.7),
            "Inside it",
            (lambda: [FadeIn(stub, scale=0.9)], 0.6),
            "Java's",
            (lambda: self.cap("Java: InetAddress.getByName(\"example.com\")  calls the stub"), 0.5),
        ])
        res_t2 = T("recursive resolver", 20).move_to(res_t)
        res_s = T("127.0.0.11 in the lab", 17, GREY_B).move_to(RES + [0, -0.22, 0])
        self.steps("It makes one call, to the address in a small settings file. That address belongs to a recursive resolver: directory enquiries.", [
            (lambda: [travel(l_pr, BLUE_M, 0.7), *self.cap("/etc/resolv.conf:   nameserver 127.0.0.11")], 0.8),
            "recursive resolver",
            (lambda: [swap(res_t, res_t2), FadeIn(res_s)], 0.8),
        ])
        self.steps("And the books are servers: the root, the com servers, and example.com's own servers, the authoritative ones.", [
            (lambda: [*self.uncap(), *self.sub(0, "who runs com")], 0.6),
            "the com servers",
            (lambda: self.sub(1, "who runs example.com"), 0.6),
            "example.com's own",
            (lambda: self.sub(2, "authoritative", GOLD_M), 0.6),
        ])

        # ---------------- scene 3: why not walk it yourself? ----------------
        BY = -1.5
        k_ms = 0.06
        x0 = -4.3
        segs, labs = VGroup(), VGroup()
        for name, ms in (("root", 46), ("com", 48), ("example.com", 16)):
            w = ms * k_ms
            r = Rectangle(width=w - 0.04, height=0.3, stroke_width=0).set_fill(BLUE_M, 0.8).move_to([x0 + w / 2, BY, 0])
            segs.add(r)
            lab = T(f"{name} {ms} ms", 17, GREY_B)
            labs.add(lab.move_to([x0 + w / 2, BY + 0.38, 0]) if ms > 20 else left_at(lab, x0 + w + 0.15, BY))
            x0 += w
        total = T("about 110 ms, for every lookup", 20, WHITE).move_to([-4.3 + 110 * k_ms / 2, BY - 0.45, 0])
        self.steps("Why the middleman? To be fair, your program could walk the books itself. A tool called dig can do exactly that, and it works.", [
            (lambda: self.cap("why the middleman?", WHITE), 0.5),
            "A tool called dig",
            (lambda: self.cap("dig +trace: walks root, com and example.com itself"), 0.5),
            "and it works",
            (lambda: [LaggedStart(*[travel(l, BLUE_M, 0.45) for l in lines], lag_ratio=0.3)], 0.8),
        ])
        self.steps("It takes three trips: 46, 48 and 16 milliseconds, about a tenth of a second, for every lookup.", [
            "46",
            (lambda: [GrowFromEdge(segs[0], LEFT), FadeIn(labs[0])], 0.5),
            "48",
            (lambda: [GrowFromEdge(segs[1], LEFT), FadeIn(labs[1])], 0.5),
            "16",
            (lambda: [GrowFromEdge(segs[2], LEFT), FadeIn(labs[2])], 0.4),
            "about a tenth",
            (lambda: [FadeIn(total, shift=0.1 * UP)], 0.5),
        ])
        crowd = Line([-6.5, 3.25, 0], [SX - SBW / 2 - 0.05, SY[0] + 0.25, 0])
        self.steps("Now multiply. If every program on the internet started at the root for every lookup, "
                   "a few root servers would answer for the whole world, all the time.", [
            (lambda: self.cap("every program on the internet, every lookup, starting at the root", RED_M), 0.5),
            "started at the root",
            (lambda: [LaggedStart(*[travel(crowd, GREY_B, 0.7) for _ in range(14)], lag_ratio=0.12)], 2.4),
            "a few root",
            (lambda: [glow(boxes[0][0], RED_M, 1.06)], 0.8),
        ])
        self.steps("So the resolver does the walking, and it remembers. Watch how.", [
            (lambda: [FadeOut(segs), FadeOut(labs), FadeOut(total), *self.cap("the resolver walks, and remembers", TEAL_M)], 0.6),
            (lambda: [glow(res_box, TEAL_M, 1.04)], 0.8),
        ])

        # ---------------- scene 4: the walk ----------------
        notes = VGroup(RoundedRectangle(corner_radius=0.14, width=NW, height=NH, stroke_color=TEAL_M, stroke_width=2.5).set_fill(fillc(TEAL_M, 0.08), 1).move_to(NC),
                       left_at(T("the resolver's notes", 18, GREY_B), NX0 + 0.25, NC[1] + NH / 2 - 0.28),
                       right_at(T("keep for", 18, GREY_B), NX1 - 0.25, NC[1] + NH / 2 - 0.28))
        empty = T("empty", 20, GREY_B).move_to(NC + [0, -0.2, 0])
        rd = T("RD: do the whole job for me", 18, BLUE_M).move_to([(PROG[0] + RES[0]) / 2 + 0.2, PROG[1] - 0.95, 0])
        self.steps("The stub sends one question to the resolver, with a flag that means: do the whole job for me. "
                   "It's called RD, recursion desired. The resolver's notes are empty.", [
            (lambda: [*self.uncap(), *self.set_ask("example.com ?", BLUE_M)], 0.5),
            "with a flag",
            (lambda: [travel(l_pr, BLUE_M, 0.8), FadeIn(rd, shift=0.1 * UP)], 0.9),
            "The resolver's notes",
            (lambda: [FadeIn(notes), FadeIn(empty)], 0.7),
        ])
        built = right_at(T("address built into its software", 17, GREY_B), SX - SBW / 2 - 0.15, SY[0] + 0.35)
        self.steps("So it starts at the top. A root server's address is built into its software, because nothing can be looked up before it.", [
            (lambda: [FadeOut(rd), glow(boxes[0][0], WHITE, 1.04)], 0.7),
            "is built into",
            (lambda: [FadeIn(built, shift=0.1 * DOWN)], 0.6),
        ])
        self.steps("It asks the same question, without that flag: just tell me what you know. Does the root know example.com's address? Pause and guess.", [
            (lambda: [FadeOut(built), travel(lines[0], BLUE_M, 0.9)], 1.0),
            "just tell me",
            (lambda: self.cap("no flag: just tell me what you know", WHITE), 0.5),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        ms = [T("46 ms", 17, GREY_B), T("48 ms", 17, GREY_B), T("16 ms", 17, GREY_B)]
        offs = [np.array([-0.2, 0.3, 0]), np.array([0, 0.25, 0]), np.array([-0.17, -0.31, 0])]
        for k in range(3):
            ms[k].move_to(lines[k].get_center() + offs[k])
        nrow = [None, None, None]

        def row(k, name, what, keep, color=WHITE, mono_what=False):
            y = NROW[k]
            g = VGroup(left_at(M(name, 18, color), NX0 + 0.25, y),
                       left_at((M if mono_what else T)(what, 18, color), NX0 + 2.15, y))
            if keep:
                g.add(right_at(M(keep, 18, color), NX1 - 0.25, y))
            nrow[k] = g
            return g

        r0 = row(0, "com", "13 servers, and their addresses", "2 days", GOLD_M)
        self.steps("No. The root is like a very senior manager. It doesn't know the answer, but it knows who to ask.", [
            (lambda: [*self.uncap(), Indicate(boxes[0][1], color=WHITE)], 0.6),
            "senior manager",
            (lambda: self.cap("doesn't know the answer, knows who to ask"), 0.5),
        ], after=0.3)
        self.steps("It replies: ask the com servers, here are 13 of them, and here are their addresses.", [
            (lambda: [travel(back(lines[0]), GOLD_M, 0.9), FadeIn(ms[0])], 1.0),
            "ask the com",
            (lambda: [edges[0].animate.set_stroke(GOLD_M, 4), glow(boxes[1][0], GOLD_M, 1.04)], 0.7),
            "here are 13",
            (lambda: [FadeOut(empty), FadeIn(r0, shift=0.1 * DOWN)], 0.6),
        ])
        self.steps("That reply is a referral. The addresses that come with it are called glue. Without them, "
                   "the resolver would have to look up the com servers' names before it could ask them anything.", [
            (lambda: self.cap("a referral: I don't know, but these servers do", GOLD_M), 0.5),
            "called glue",
            (lambda: [*self.cap("glue: the referred servers' addresses, sent along", GOLD_M), Indicate(r0[1], color=GOLD_M)], 0.7),
        ])
        r1 = row(1, "example.com", "ask hera or elliott", "2 days", GOLD_M)
        self.steps("The resolver asks a com server. Another referral, one level down: example.com lives on two servers run by Cloudflare, "
                   "hera and elliott, with their addresses.", [
            (lambda: [*self.uncap(), edges[0].animate.set_stroke(GREY_C, 2.5), travel(lines[1], BLUE_M, 0.9)], 1.0),
            "Another referral",
            (lambda: [travel(back(lines[1]), GOLD_M, 0.9), FadeIn(ms[1])], 1.0),
            "example.com lives",
            (lambda: [edges[1].animate.set_stroke(GOLD_M, 4), *self.sub(2, "hera and elliott", GOLD_M),
                      *self.cap("example.com's servers: hera and elliott, run by Cloudflare")], 0.7),
            "hera and elliott",
            (lambda: [FadeIn(r1, shift=0.1 * DOWN)], 0.6),
        ])
        self.ttl = ValueTracker(300)
        r2 = row(2, "example.com", f"{A1}, {A2}", None, GREEN_M, mono_what=True)
        ttl_m = always_redraw(lambda: right_at(M(f"{int(round(self.ttl.get_value()))} s", 18, GREEN_M), NX1 - 0.25, NROW[2]))
        self.steps("Third question, to hera. This time, an answer: two addresses, marked authoritative, the original.", [
            (lambda: [edges[1].animate.set_stroke(GREY_C, 2.5), travel(lines[2], BLUE_M, 0.9)], 1.0),
            "This time",
            (lambda: [travel(back(lines[2]), GREEN_M, 0.9), FadeIn(ms[2])], 1.0),
            "marked authoritative",
            (lambda: [glow(boxes[2][0], GOLD_M, 1.04), *self.cap("AA: authoritative answer, the original", GOLD_M)], 0.7),
        ])
        self.steps("Each may be kept for 300 seconds, its time to live.", [
            (lambda: [FadeIn(r2, shift=0.1 * DOWN), FadeIn(ttl_m)], 0.6),
            "its time to live",
            (lambda: self.cap("TTL, time to live: how long anyone may keep this copy"), 0.5),
        ])
        self.steps("The resolver passes them to the stub, marked as a copy. Three trips for the resolver; one question from your program.", [
            (lambda: [*self.uncap(), travel(back(l_pr), GREEN_M, 0.8)], 0.9),
            (lambda: self.set_ask(f"{A1}, {A2}", GREEN_M), 0.5),
            "marked as a copy",
            (lambda: self.cap("a copy: no AA", GREY_B), 0.5),
            "Three trips",
            (lambda: [LaggedStart(*[Indicate(m, color=WHITE) for m in ms], lag_ratio=0.3)], 1.0),
        ])

        # ---------------- scene 5: the names ----------------
        self.steps("Now the names. The resolver that walks for you is a recursive resolver. "
                   "The just-tell-me-what-you-know questions it sends are iterative queries.", [
            (lambda: [*self.cap("recursive resolver: does the whole walk for you", TEAL_M), glow(res_box, TEAL_M, 1.04)], 0.8),
            "The just",
            (lambda: [*self.cap("iterative queries: just tell me what you know", WHITE),
                      LaggedStart(*[l.animate(rate_func=there_and_back).set_stroke(WHITE, 5) for l in lines], lag_ratio=0.25)], 1.2),
        ])

        # ---------------- scene 6: the notes ----------------
        self.steps("And it remembered everything. The referrals came with a time to live of 172,800 seconds: two days. The answer, 300 seconds: five minutes.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(*ms))], 0.5),
            "The referrals",
            (lambda: [Indicate(r0[2], color=GOLD_M, scale_factor=1.3), Indicate(r1[2], color=GOLD_M, scale_factor=1.3),
                      *self.cap("172,800 seconds = two days")], 0.9),
            "The answer, 300",
            (lambda: [Indicate(ttl_m, color=GREEN_M, scale_factor=1.3), *self.cap("300 seconds = five minutes")], 0.9),
        ])
        tree = VGroup(*boxes, edges, *[s for s in self.subs if s is not None], *lines)
        self.steps("200 seconds later, another program asks for example.com. The resolver answers from its notes in one short trip, "
                   "and says the copy has 100 seconds left.", [
            (lambda: [*self.clear_ask(), self.ttl.animate(rate_func=linear).set_value(100), tree.animate.set_opacity(0.3),
                      *self.cap("200 seconds later")], 1.6),
            "another program",
            (lambda: [*self.set_ask("example.com ?", BLUE_M), travel(l_pr, BLUE_M, 0.7)], 0.8),
            "answers from its notes",
            (lambda: [Indicate(r2, color=GREEN_M, scale_factor=1.05), travel(back(l_pr), GREEN_M, 0.7)], 0.9),
            (lambda: self.set_ask(f"{A1}, {A2}", GREEN_M), 0.5),
            "100 seconds left",
            (lambda: self.cap("one short trip, no tree; the copy has 100 seconds left", GREEN_M), 0.5),
        ])
        self.steps("That's why a few root servers can serve the whole internet. A busy resolver answers almost every question from its notes, "
                   "and asks the root again only every two days. Lucky root.", [
            (lambda: [boxes[0].animate.set_opacity(1), self.subs[0].animate.set_opacity(1)], 0.6),
            "A busy resolver",
            (lambda: [LaggedStart(*[Succession(travel(l_pr, BLUE_M, 0.35), travel(back(l_pr), GREEN_M, 0.35)) for _ in range(4)], lag_ratio=0.3)], 1.3),
            "Lucky root",
            (lambda: [Wiggle(boxes[0], scale_value=1.05, rotation_angle=0.02 * TAU)], 0.9),
        ])

        # ---------------- scene 7: the catch ----------------
        self.steps("The catch: every note is a copy. For up to five minutes, the resolver hands out its copy without asking anyone. "
                   "If the owner changes the address, the copies don't hear about it. Fast answers and old answers come together.", [
            (lambda: [boxes[0].animate.set_opacity(0.3), self.subs[0].animate.set_opacity(0.3), *self.cap("every note is a copy", YELLOW_M)], 0.6),
            "For up to five",
            (lambda: [r2[1].animate.set_color(GREY_B), Indicate(ttl_m, color=YELLOW_M, scale_factor=1.3)], 0.8),
            "If the owner",
            (lambda: [boxes[2].animate.set_opacity(1), self.subs[2].animate.set_opacity(1), glow(boxes[2][0], GOLD_M, 1.04)], 0.8),
            "Fast answers",
            (lambda: self.cap("fast answers and old answers come together", YELLOW_M), 0.5),
        ])

        # ---------------- scene 8: the moral, and a check ----------------
        self.steps("So, who did the asking? Your program asked one helper. The helper walked the tree, one referral at a time, "
                   "and wrote down everything it learned, each note with its own expiry.", [
            (lambda: [tree.animate.set_opacity(1), r2[1].animate.set_color(GREEN_M), *self.clear_ask(), *self.cap("who did the asking?", WHITE)], 0.7),
            "Your program asked",
            (lambda: [travel(l_pr, BLUE_M, 0.7)], 0.8),
            "The helper walked",
            (lambda: [Succession(*[travel(l, BLUE_M, 0.5) for l in lines])], 1.6),
            "and wrote down",
            (lambda: [LaggedStart(*[Indicate(r, color=TEAL_M, scale_factor=1.04) for r in (r0, r1, r2)], lag_ratio=0.3)], 1.0),
        ])
        gone = T("expired", 18, RED_M)
        self.steps("One quick check. Ten minutes later, someone asks for example.com again. Which servers does the resolver have to ask? Pause and think.", [
            (lambda: [*self.cap("ten minutes later", WHITE), *self.set_ask("example.com ?", BLUE_M)], 0.5),
            "Ten minutes",
            (lambda: [self.ttl.animate(rate_func=linear).set_value(0)], 1.2),
            (lambda: [FadeOut(r2[1]), FadeOut(ttl_m), FadeIn(gone.move_to([NC[0] + 0.3, NROW[2], 0]))], 0.5),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.ttl.set_value(300)
        r2b = row(2, "example.com", f"{A1}, {A2}", "300 s", GREEN_M, mono_what=True)
        self.steps("Only example.com's own servers, hera or elliott. The five-minute answer has run out, but the referrals last two days. "
                   "The root and com get a rest.", [
            (lambda: [*self.uncap(), boxes[0].animate.set_opacity(0.3), boxes[1].animate.set_opacity(0.3),
                      self.subs[0].animate.set_opacity(0.3), self.subs[1].animate.set_opacity(0.3),
                      lines[0].animate.set_opacity(0.3), lines[1].animate.set_opacity(0.3), travel(lines[2], BLUE_M, 0.8)], 0.9),
            (lambda: [travel(back(lines[2]), GREEN_M, 0.8), glow(boxes[2][0], GOLD_M, 1.04)], 0.9),
            "The five-minute",
            (lambda: [FadeOut(gone), FadeIn(r2b[1]), FadeIn(r2b[2])], 0.5),
            "but the referrals",
            (lambda: [Indicate(r0[2], color=GOLD_M, scale_factor=1.3), Indicate(r1[2], color=GOLD_M, scale_factor=1.3)], 0.9),
        ], after=0.3)
        self.play(*self.cap("one question, one helper, notes with expiry dates", TEAL_M, 26), run_time=0.7)
        self.wait(2.0)
