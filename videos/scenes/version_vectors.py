from sfz import *

# card numbers are said the way people read them; the region names are letters
SAY.insert(0, (r"\b4417\b", "forty four seventeen"))
SAY.insert(0, (r"\b5310\b", "fifty three ten"))
SAY.insert(0, (r"\b2290\b", "twenty two ninety"))
SAY.insert(0, (r"\bEU\b", "E U"))
SAY.insert(0, (r"\bUS\b", "U S"))
# "client A" reads as "client uh"; "eh" lands on the letter
SAY.insert(0, (r"\b[Cc]lient A\b", "client eh"))

RP = {"eu": np.array([-3.6, 0.95, 0]), "us": np.array([3.6, 0.95, 0])}   # replicas
RW, RH = 4.6, 3.0
VW, VH = 4.0, 0.95                                                        # one stored version
SLOT = [1.35, 0.2]                                                        # y of the first and second version
CLP = {"eu": np.array([-3.6, -1.75, 0]), "us": np.array([3.6, -1.75, 0])}
PC = np.array([0, -1.78, 0])                                              # the comparison panel
PW, PH = 4.2, 1.7
COLX = [-1.05, 0.65, 1.45]                                                # label, eu, us columns
ROWY = [-1.18, -1.53, -1.88, -2.23]                                       # header and three rows
STY = -3.2


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


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def replica(k):
    c = RP[k]
    r = RoundedRectangle(corner_radius=0.16, width=RW, height=RH, stroke_color=WHITE, stroke_width=2.5).set_fill(BLACK, 1)
    r.move_to(c)
    return VGroup(r, T(f"{k.upper()} replica", 24).move_to(c + (RH / 2 - 0.33) * UP))


def vline(e, u, ce=WHITE, cu=WHITE):
    """A version vector: one counter per replica."""
    g = VGroup(M("eu", 18, GREY_B), M(str(e), 18, ce), M("us", 18, GREY_B), M(str(u), 18, cu))
    g[1].next_to(g[0], RIGHT, buff=0.15)
    g[2].next_to(g[1], RIGHT, buff=0.45)
    g[3].next_to(g[2], RIGHT, buff=0.15)
    return g


def version(k, slot, cards, line2, color=WHITE):
    c = np.array([RP[k][0], SLOT[slot], 0])
    r = RoundedRectangle(corner_radius=0.1, width=VW, height=VH, stroke_color=color, stroke_width=2.5).set_fill(fillc(color), 1)
    r.move_to(c)
    s = M("blocked: " + " ".join(cards), 18, WHITE).move_to(c + 0.2 * UP)
    if isinstance(line2, str):
        line2 = M(line2, 18, GREY_B)
    line2.move_to(c + 0.21 * DOWN)
    return VGroup(r, s, line2)


def client(k, label):
    return mbox(label, GREY_B, w=2.0, h=0.62, size=18).move_to(CLP[k])


def heading(s, color=WHITE):
    return T(s, 26, color).move_to([-6.5, 3.15, 0], aligned_edge=LEFT)


def status(s, color=GREY_B):
    return T(s, 22, color).move_to([0, STY, 0])


def cell(s, col, row, color=WHITE, mono=True):
    t = (M(s, 18, color) if mono else T(s, 19, color))
    if col == 0:
        return t.move_to([PC[0] + COLX[0], ROWY[row], 0])
    return t.move_to([PC[0] + COLX[col], ROWY[row], 0])


class VersionVectors(Base):
    """repl-08, section 2: one key (the blocked-card set) on two replicas. Client A blocks card-4417 through EU while
    client B blocks card-5310 through US. Last write wins keeps EU's version (stamped 1 ms later) and drops 5310 with
    no error. Version vectors: [eu 3, us 0] against [eu 2, us 1], each ahead on one entry, so they are concurrent;
    both are kept as siblings, a client merges them and writes [eu 4, us 1], which descends from both."""

    def construct(self):
        self.title_card("Version vectors", "two writes that never saw each other")

        rep = {k: replica(k) for k in RP}
        v = {k: version(k, 0, ["2290"], "") for k in RP}
        h1 = heading("one key: the set of blocked cards")
        self.steps("Two regions keep copies of one key: the set of blocked cards. Both copies say card 2290 is blocked.", [
            (lambda: [LaggedStart(*[FadeIn(rep[k], scale=0.96) for k in RP], lag_ratio=0.3)], 0.9),
            (lambda: [FadeIn(h1, shift=0.1 * DOWN)], 0.6),
            "Both copies",
            (lambda: [*[FadeIn(v[k], scale=0.95) for k in RP]], 0.8),
        ])

        cl = {"eu": client("eu", "client A"), "us": client("us", "client B")}
        ca = {k: Arrow(cl[k].get_top() + 0.06 * UP, [CLP[k][0], RP[k][1] - RH / 2 - 0.06, 0], buff=0, stroke_width=3,
                       color=GREY_B, max_tip_length_to_length_ratio=0.2) for k in RP}
        self.steps("At the same moment, client A blocks card 4417 through EU, and client B blocks card 5310 through US. "
                   "Neither has seen the other's write.", [
            (lambda: [*[FadeIn(cl[k], shift=0.1 * UP) for k in RP], *[GrowArrow(ca[k]) for k in RP]], 0.8),
            "client A blocks",
            (lambda: [travel(ca["eu"], YELLOW_M, 0.6)], 0.6),
            (lambda: [Transform(v["eu"], version("eu", 0, ["2290", "4417"], ""))], 0.6),
            "client B blocks",
            (lambda: [travel(ca["us"], YELLOW_M, 0.6)], 0.6),
            (lambda: [Transform(v["us"], version("us", 0, ["2290", "5310"], ""))], 0.6),
        ])

        sync = DoubleArrow([RP["eu"][0] + RW / 2 + 0.1, SLOT[0], 0], [RP["us"][0] - RW / 2 - 0.1, SLOT[0], 0], buff=0,
                           stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.12)
        q = T("?", 40, GREY_B).move_to([0, SLOT[1], 0])
        self.steps("Then the replicas swap versions. Which set should each one keep?", [
            (lambda: [GrowFromCenter(sync)], 0.6),
            (lambda: [travel(sync, YELLOW_M, 0.8), travel(Line(sync.get_end(), sync.get_start()), YELLOW_M, 0.8)], 0.8),
            "Which set",
            (lambda: [FadeIn(q, scale=0.8)], 0.5),
        ])

        h2 = heading("rule 1: last write wins")
        self.steps("Last write wins stamps every write with the clock and keeps the higher stamp. "
                   "EU's write says 2 milliseconds past ten. US's says 1.", [
            (lambda: [FadeOut(q), FadeOut(h1), FadeIn(h2, shift=0.1 * DOWN)], 0.6),
            "EU's write",
            (lambda: [Transform(v["eu"], version("eu", 0, ["2290", "4417"], "stamped 10:00:00.002"))], 0.7),
            "US's says",
            (lambda: [Transform(v["us"], version("us", 0, ["2290", "5310"], "stamped 10:00:00.001"))], 0.7),
        ])

        lost = status("card 5310: lost, and client B was told OK", RED_M)
        self.steps("So both replicas keep EU's set. Card 5310 is gone, though client B was told its block succeeded.", [
            (lambda: [glow(v["eu"][0], GREEN_M)], 0.7),
            (lambda: [travel(sync, GREEN_M, 0.7)], 0.7),
            (lambda: [Transform(v["us"], version("us", 0, ["2290", "4417"], "stamped 10:00:00.002"))], 0.7),
            "Card 5310",
            (lambda: [FadeIn(lost, shift=0.1 * UP), glow(cl["us"][0], RED_M)], 0.8),
        ])

        h3 = heading("rule 2: version vectors")
        self.steps("The clock can't tell what each writer had seen. A version vector can. Each version keeps one counter per replica: how many of that replica's "
                   "writes it has seen. The starting set had seen two from EU and none from US.", [
            (lambda: [FadeOut(lost), FadeOut(h2), FadeIn(h3, shift=0.1 * DOWN),
                      *[Transform(v[k], version(k, 0, ["2290"], "")) for k in RP]], 0.8),
            "one counter per replica",
            (lambda: [*[Transform(v[k], version(k, 0, ["2290"], vline(2, 0))) for k in RP]], 0.8),
            "The starting set",
            (lambda: [*[Indicate(v[k][2], color=YELLOW_M, scale_factor=1.1) for k in RP]], 0.9),
        ])

        self.steps("A write adds one to its own replica's counter. A's write through EU becomes EU 3, US 0. "
                   "B's write through US becomes EU 2, US 1.", [
            "A's write",
            (lambda: [travel(ca["eu"], YELLOW_M, 0.5)], 0.5),
            (lambda: [Transform(v["eu"], version("eu", 0, ["2290", "4417"], vline(3, 0, YELLOW_M)))], 0.7),
            "B's write",
            (lambda: [travel(ca["us"], YELLOW_M, 0.5)], 0.5),
            (lambda: [Transform(v["us"], version("us", 0, ["2290", "5310"], vline(2, 1, WHITE, YELLOW_M)))], 0.7),
        ])

        panel = RoundedRectangle(corner_radius=0.12, width=PW, height=PH, stroke_color=GREY_B, stroke_width=2).set_fill(BLACK, 1)
        panel.move_to(PC)
        hdr = VGroup(cell("eu", 1, 0, GREY_B), cell("us", 2, 0, GREY_B))
        rA = VGroup(cell("A's write", 0, 1, WHITE, False), cell("3", 1, 1), cell("0", 2, 1))
        rB = VGroup(cell("B's write", 0, 2, WHITE, False), cell("2", 1, 2), cell("1", 2, 2))
        self.steps("To compare two versions, line the counters up. If every counter in one is at least as big as in the other, "
                   "its writer saw the other version, so it may replace it.", [
            (lambda: [FadeIn(panel), FadeIn(hdr)], 0.6),
            (lambda: [FadeIn(rA, shift=0.1 * RIGHT)], 0.5),
            (lambda: [FadeIn(rB, shift=0.1 * RIGHT)], 0.5),
            "If every counter",
            (lambda: [glow(panel, GREY_A, 1.03)], 1.0),
        ])

        conc = status("each is ahead somewhere: concurrent", GOLD_M)
        self.steps("Here A's version is ahead on EU, and B's is ahead on US. Each holds a write the other never saw. "
                   "They're concurrent.", [
            (lambda: [rA[1].animate.set_color(GREEN_M).scale(1.3), rB[1].animate.set_color(GREY_D)], 0.7),
            "and B's is ahead",
            (lambda: [rB[2].animate.set_color(GREEN_M).scale(1.3), rA[2].animate.set_color(GREY_D)], 0.7),
            "They're concurrent",
            (lambda: [FadeIn(conc, shift=0.1 * UP)], 0.6),
        ])

        sib = {"eu": version("eu", 1, ["2290", "5310"], vline(2, 1)), "us": version("us", 1, ["2290", "4417"], vline(3, 0))}
        sl = status("both kept, as siblings", GOLD_M)
        self.steps("So neither may replace the other. Each replica keeps both, as siblings, and the next read returns both.", [
            (lambda: [travel(sync, YELLOW_M, 0.7), travel(Line(sync.get_end(), sync.get_start()), YELLOW_M, 0.7)], 0.7),
            (lambda: [Transform(v["eu"], version("eu", 0, ["2290", "4417"], vline(3, 0))),
                      Transform(v["us"], version("us", 0, ["2290", "5310"], vline(2, 1))),
                      *[FadeIn(sib[k], shift=0.15 * DOWN) for k in RP], Transform(conc, sl)], 0.8),
            "the next read",
            (lambda: [*[glow(v[k][0], GOLD_M, 1.03) for k in RP], *[glow(sib[k][0], GOLD_M, 1.03) for k in RP]], 0.9),
        ])

        merged = {k: version(k, 0, ["2290", "4417", "5310"], vline(4, 1, YELLOW_M), GREEN_M) for k in RP}
        rM = VGroup(cell("merged", 0, 3, GREEN_M, False), cell("4", 1, 3, GREEN_M), cell("1", 2, 3, GREEN_M))
        self.steps("Client A reads both, blocks all three cards, and writes back through EU with a vector that covers both: "
                   "EU 4, US 1.", [
            (lambda: [travel(Line(ca["eu"].get_end(), ca["eu"].get_start()), GOLD_M, 0.6)], 0.6),
            (lambda: [Transform(cl["eu"], client("eu", "A merges"))], 0.5),
            "and writes back",
            (lambda: [travel(ca["eu"], GREEN_M, 0.6)], 0.6),
            (lambda: [FadeOut(sib["eu"], shift=0.15 * UP), Transform(v["eu"], merged["eu"])], 0.8),
            "EU 4",
            (lambda: [FadeIn(rM, shift=0.1 * RIGHT), rA[1].animate.set_color(WHITE).scale(1 / 1.3),
                      rB[2].animate.set_color(WHITE).scale(1 / 1.3), rA[2].animate.set_color(WHITE),
                      rB[1].animate.set_color(WHITE)], 0.7),
        ])

        done = status("no write lost", GREEN_M)
        self.steps("It's at least as big as both siblings on every counter, so it replaces them on both replicas. "
                   "No write is lost.", [
            (lambda: [glow(panel, GREEN_M, 1.03), Indicate(rM[1], color=GREEN_M), Indicate(rM[2], color=GREEN_M)], 0.9),
            "so it replaces",
            (lambda: [travel(sync, GREEN_M, 0.7)], 0.7),
            (lambda: [FadeOut(sib["us"], shift=0.15 * UP), Transform(v["us"], merged["us"])], 0.8),
            "No write",
            (lambda: [Transform(conc, done)], 0.6),
        ])

        self.steps("One write may replace another only if it saw it. The version vector says whether it did, "
                   "and when neither saw the other, keep both and merge.", [
            (lambda: [glow(v["eu"][0], GREEN_M), glow(v["us"][0], GREEN_M)], 1.0),
            "The version vector",
            (lambda: [*[Indicate(v[k][2], color=YELLOW_M, scale_factor=1.1) for k in RP]], 1.0),
            "keep both",
            (lambda: [glow(panel, GOLD_M, 1.03)], 1.0),
        ])
        self.wait(0.6)
