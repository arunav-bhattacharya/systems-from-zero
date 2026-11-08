from sfz import *

# The amount, said the way people say a price.
SAY.insert(0, (r"\b12\.50\b", "twelve fifty"))
# Kokoro says "IDE-mpotency" (no vowel after the d); spell out "eye-dem-potency".
SAY.insert(0, (r"\bidempotency\b", "eye-dem-potency"))


def _layer(m):
    """Text above chips above arrows above boxes, so an opaque box never hides its own label."""
    for x in m.get_family():
        if isinstance(x, Text):
            x.set_z_index(4)
        elif isinstance(x, Arrow):
            x.set_z_index(1)
        elif isinstance(x, RoundedRectangle) and 0 < x.get_fill_opacity() < 0.5:
            x.set_z_index(2)


def _defer_add(anim):
    """Make each step that is not an introducer add its mobject when the step starts."""
    if isinstance(anim, AnimationGroup):
        for a in anim.animations:
            _defer_add(a)
        return
    if anim.is_introducer() or anim.mobject is None:
        return
    orig = anim._setup_scene

    def setup(scene, orig=orig, anim=anim):
        orig(scene)
        if scene is not None and anim.mobject not in scene.get_mobject_family_members():
            scene.add(anim.mobject)
    anim._setup_scene = setup


class Layered(VoiceScene):
    def add_mobjects_from_animations(self, animations):
        """Manim adds every mobject of a Succession when the Succession starts, so a later step that moves or
        transforms a mobject not yet on screen would show it too early. Add the first step's mobjects now and
        each later step's when that step starts."""
        curr = self.get_mobject_family_members()

        def visit(a, first):
            if isinstance(a, Succession):
                for i, s in enumerate(a.animations):
                    if first and i == 0:
                        visit(s, True)
                    else:
                        _defer_add(s)
                return
            if isinstance(a, AnimationGroup):
                for s in a.animations:
                    visit(s, first)
                return
            if a.is_introducer() or a.mobject is None:
                return
            if a.mobject not in curr:
                self.add(a.mobject)
                curr.extend(a.mobject.get_family())

        for a in animations:
            visit(a, True)

    def play(self, *anims, **kw):
        for a in anims:
            _layer(a.mobject)
            if getattr(a, "target_mobject", None) is not None:
                _layer(a.target_mobject)
        for m in self.mobjects:
            _layer(m)
        super().play(*anims, **kw)
        for m in self.mobjects:
            _layer(m)


def counter(fmt, value, place, size=22, color=WHITE):
    """A text that follows value() each frame; each distinct text is built once."""
    cache = {}

    def make():
        s = fmt(value())
        if s not in cache:
            cache[s] = T(s, size, color)
        return place(cache[s].copy())
    return always_redraw(make)


SX, IX, BY = -4.8, 4.8, 1.0            # shop and issuer centres
QY, RY = 1.75, 0.25                    # request lane and reply lane
QC, RC = 1.3, 0.7                      # where message chips ride, just inside the lanes
LANE = 3.2                             # lanes run from -LANE to LANE
CARD_X = [-5.45 + 2.18 * i for i in range(6)]
CARD_Y = -2.35
NEVER, ALREADY, LATER = TEAL_M, RED_M, GOLD_M


def side(x, color=WHITE):
    r = RoundedRectangle(corner_radius=0.16, width=3.0, height=2.2, stroke_color=color, stroke_width=3)
    return r.set_fill(BLACK, opacity=1).move_to([x, BY, 0])


def iss(l1, l2="", c1=WHITE, c2=GREY_B):
    a = T(l1, 20, c1).move_to([IX, BY - 0.02, 0])
    b = (T(l2, 20, c2) if l2 else T(".", 20).set_opacity(0)).move_to([IX, BY - 0.55, 0])
    return VGroup(a, b)


def card(i, title, outcome, color):
    r = RoundedRectangle(corner_radius=0.12, width=2.1, height=1.15, stroke_color=GREY_D, stroke_width=2).set_fill(BLACK, 1)
    t = T(title, 20).move_to([0, 0.22, 0])
    o = T(outcome, 20, color).move_to([0, -0.24, 0])
    return VGroup(r, t, o).move_to([CARD_X[i], CARD_Y, 0])


def req(x=-LANE + 0.6):
    return chip("pay-1", YELLOW_M, 20, mono=True).move_to([x, QC, 0])


def rep(x=LANE - 0.65):
    return chip("A00001", GREEN_M, 20, mono=True).move_to([x, RC, 0])


class PartialFailure(Layered):
    """dist-01: one payment, a 2-second timeout and six worlds that all look like silence to the shop
    (request lost or queued, issuer crashed or paused, reply lost or slow); then the idempotency-key retry.
    Times from the lesson's SilenceDemo: 50 ms per charge, 5 s for the slow cases."""

    def construct(self):
        self.title_card("Partial failure", "six ways to hear nothing")

        shop, issuer = side(SX), side(IX)
        shop_n, iss_n = T("shop", 28).move_to([SX, BY + 0.62, 0]), T("issuer", 28).move_to([IX, BY + 0.62, 0])
        shop_l = M("pay-1: 12.50", 20).move_to([SX, BY - 0.02, 0])
        lines = iss("charges cards", "50 ms per charge")
        q = Arrow([-LANE, QY, 0], [LANE, QY, 0], buff=0, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.03)
        r = Arrow([LANE, RY, 0], [-LANE, RY, 0], buff=0, stroke_width=3, color=GREY_B, max_tip_length_to_length_ratio=0.03)
        q_l = T("request", 22, GREY_B).move_to([0, QY + 0.3, 0])
        r_l = T("reply", 22, GREY_B).move_to([0, RY - 0.3, 0])

        self.beat("A shop sends a card issuer an authorization for 12.50, across the network. "
                  "Three parts can now fail on their own: the shop, the network, and the issuer.",
                  Succession(AnimationGroup(FadeIn(VGroup(shop, shop_n, shop_l)), FadeIn(VGroup(issuer, iss_n, lines)), run_time=1.0),
                             AnimationGroup(GrowArrow(q), GrowArrow(r), FadeIn(q_l), FadeIn(r_l), run_time=1.0), Wait(3.0),
                             LaggedStart(Indicate(shop_n, color=YELLOW_M), Indicate(VGroup(q_l, r_l), color=YELLOW_M),
                                         Indicate(iss_n, color=YELLOW_M), lag_ratio=0.6, run_time=2.6)), run_time=8.6)

        clock = ValueTracker(0)
        timer = counter(lambda v: f"timer: {int(v):,} ms", clock.get_value, lambda m: m.move_to([SX, BY - 0.55, 0]), 22, GREY_B)
        view = T("shop sees: no reply", 24, GOLD_M).move_to([SX, -0.75, 0])
        c = req()
        self.beat("The shop starts a two second timer. The timer runs out, and no reply has come. Where is the request?",
                  Succession(AnimationGroup(FadeIn(timer), FadeIn(c, shift=0.2 * RIGHT), run_time=0.5),
                             AnimationGroup(clock.animate(rate_func=linear).set_value(2000), c.animate(rate_func=linear).move_to([0, QC, 0]),
                                            run_time=2.6),
                             FadeIn(view, shift=0.2 * UP, run_time=0.6)), run_time=4.6)
        timer.clear_updaters()
        out = T("timed out", 22, RED_M).move_to([SX, BY - 0.55, 0])
        self.remove(timer)
        self.add(out)

        # ---- world 1: the request is lost ------------------------------------------------------------------
        x1 = tick(False, 0.22).next_to(c, RIGHT, buff=0.2)
        cards = [card(0, "request lost", "not charged", NEVER), card(1, "request queued", "charged later", LATER),
                 card(2, "issuer crashed", "not charged", NEVER), card(3, "issuer paused", "charged later", LATER),
                 card(4, "reply lost", "already charged", ALREADY), card(5, "reply slow", "already charged", ALREADY)]
        self.beat("It may have been lost on the way. The issuer never saw it, and the card is not charged.",
                  Succession(Create(x1, run_time=0.6), Wait(0.6), AnimationGroup(FadeOut(c), FadeOut(x1), run_time=0.6),
                             Transform(lines, iss("never saw pay-1"), run_time=0.7), Wait(0.4), FadeIn(cards[0], shift=0.2 * UP, run_time=0.6)),
                  run_time=4.6)

        # ---- world 2: the request is queued ----------------------------------------------------------------
        c = req(0)
        wait_l = T("queued", 22, GREY_B).move_to([0, RC, 0])
        self.beat("It may be stuck in a queue. It reaches the issuer at five seconds, and the card is charged then, "
                  "long after the shop gave up.",
                  Succession(AnimationGroup(Transform(lines, iss("nothing yet")), FadeIn(c), FadeIn(wait_l), run_time=0.7), Wait(1.4),
                             AnimationGroup(FadeOut(wait_l), c.animate.move_to([LANE - 0.6, QC, 0]), run_time=1.0), FadeOut(c, run_time=0.3),
                             Transform(lines, iss("charged at 5,050 ms", "", GOLD_M), run_time=0.7), Wait(0.8),
                             FadeIn(cards[1], shift=0.2 * UP, run_time=0.6)), run_time=6.4)

        # ---- world 3: the issuer crashed -------------------------------------------------------------------
        c = req()
        self.beat("The issuer may have crashed before it charged the card. Nobody is left to charge it.",
                  Succession(AnimationGroup(Transform(lines, iss("charges cards", "50 ms per charge")), FadeIn(c), run_time=0.5),
                             c.animate(run_time=1.0).move_to([LANE - 0.6, QC, 0]), FadeOut(c, run_time=0.3),
                             AnimationGroup(issuer.animate.set_stroke(RED_M), Transform(lines, iss("crashed", "process gone", RED_M)),
                                            run_time=0.7), Wait(0.6), FadeIn(cards[2], shift=0.2 * UP, run_time=0.6)), run_time=4.6)

        # ---- world 4: the issuer is paused -----------------------------------------------------------------
        self.beat("Or the issuer is paused by a long garbage collection. The request waits in its buffer, "
                  "and at five seconds the issuer wakes up and charges the card.",
                  Succession(AnimationGroup(issuer.animate.set_stroke(GREY_D), iss_n.animate.set_color(GREY_B),
                                            Transform(lines, iss("paused: 5 s GC", "pay-1 in its buffer", GREY_B)), run_time=0.8),
                             Wait(3.0), AnimationGroup(issuer.animate.set_stroke(WHITE), iss_n.animate.set_color(WHITE),
                                                       Transform(lines, iss("charged at 5,050 ms", "", GOLD_M)), run_time=0.8),
                             Wait(0.6), FadeIn(cards[3], shift=0.2 * UP, run_time=0.6)), run_time=7.0)

        # ---- world 5: the reply is lost --------------------------------------------------------------------
        c, a = req(), rep()
        x5 = tick(False, 0.22).next_to(rep(0), LEFT, buff=0.2)
        self.beat("The card may have been charged at 51 milliseconds, and the reply was lost on the way back.",
                  Succession(FadeIn(c, run_time=0.3), c.animate(run_time=0.8).move_to([LANE - 0.6, QC, 0]), FadeOut(c, run_time=0.2),
                             Transform(lines, iss("charged at 51 ms", "code A00001", ALREADY), run_time=0.6),
                             FadeIn(a, run_time=0.3), a.animate(run_time=0.8).move_to([0, RC, 0]), Create(x5, run_time=0.5),
                             AnimationGroup(FadeOut(a), FadeOut(x5), run_time=0.4), FadeIn(cards[4], shift=0.2 * UP, run_time=0.6)),
                  run_time=5.6)

        # ---- world 6: the reply is slow --------------------------------------------------------------------
        a = rep(0)
        slow_l = T("slow", 22, GREY_B).move_to([0, QC, 0])
        late_l = T("lands at 5,051 ms", 20, GREY_B).move_to([-0.95, RC, 0])
        self.beat("The reply may just be slow. It lands at five seconds, after the shop has already decided.",
                  Succession(AnimationGroup(FadeIn(a), FadeIn(slow_l), run_time=0.6), Wait(1.2),
                             AnimationGroup(FadeOut(slow_l), a.animate.move_to([-LANE + 0.65, RC, 0]), run_time=1.0),
                             AnimationGroup(FadeOut(a), FadeIn(late_l), run_time=0.5), Wait(0.8),
                             AnimationGroup(FadeOut(late_l), FadeIn(cards[5], shift=0.2 * UP), run_time=0.6)),
                  run_time=5.4)

        # ---- the shop can't tell ---------------------------------------------------------------------------
        outs = [cd[2] for cd in cards]
        self.beat("The shop sees the same thing in all six worlds: no reply. In two, the card was never charged. "
                  "In two, it already was. In two, it will be.",
                  Succession(AnimationGroup(Transform(lines, iss("charges cards", "50 ms per charge")), run_time=0.6),
                             Indicate(view, color=GOLD_M, run_time=1.2), Wait(1.0),
                             AnimationGroup(Indicate(outs[0], color=NEVER), Indicate(outs[2], color=NEVER), run_time=1.1), Wait(0.3),
                             AnimationGroup(Indicate(outs[4], color=ALREADY), Indicate(outs[5], color=ALREADY), run_time=1.1), Wait(0.3),
                             AnimationGroup(Indicate(outs[1], color=LATER), Indicate(outs[3], color=LATER), run_time=1.1)),
                  run_time=8.4)

        self.beat("Waiting longer doesn't settle it. Whatever timeout you pick, a queued request or a paused issuer can act after it.",
                  Succession(Wait(1.6), AnimationGroup(cards[1][0].animate.set_stroke(LATER), cards[3][0].animate.set_stroke(LATER),
                                                       run_time=0.8), Wait(1.2),
                             AnimationGroup(cards[1][0].animate.set_stroke(GREY_D), cards[3][0].animate.set_stroke(GREY_D),
                                            run_time=0.8)), run_time=6.4)

        unknown = T("yes, no, or unknown", 26, GOLD_M).move_to([SX, -0.75, 0])
        twice = [T("charged twice", 20, RED_M).move_to(cards[i][2]) for i in (1, 3, 4, 5)]
        self.beat("So a remote call has three outcomes: yes, no, and unknown. If the shop calls unknown a failure, "
                  "the customer pays again, and in four worlds the card is charged twice.",
                  Succession(Transform(view, unknown, run_time=0.8), Wait(3.4),
                             AnimationGroup(*[Transform(cards[i][2], t) for i, t in zip((1, 3, 4, 5), twice)],
                                            *[cards[i][0].animate.set_stroke(RED_M) for i in (1, 3, 4, 5)], run_time=0.9)),
                  run_time=9.0)

        # ---- the way out: the same key -------------------------------------------------------------------
        key_l = M("key: pay-1", 20, YELLOW_M).move_to([SX, BY - 0.55, 0])
        c = chip("pay-1 again", YELLOW_M, 20, mono=True).move_to([-LANE + 0.95, QC, 0])
        self.beat("The way out is to retry with the same idempotency key, an id the shop creates once for this payment.",
                  Succession(AnimationGroup(Transform(out, key_l), Transform(view, T("shop sees: no reply", 24, GOLD_M).move_to([SX, -0.75, 0])),
                                            *[Transform(cards[i][2], T(o, 20, col).move_to(cards[i][2]))
                                              for i, (o, col) in enumerate([("not charged", NEVER), ("charged later", LATER),
                                                                            ("not charged", NEVER), ("charged later", LATER),
                                                                            ("already charged", ALREADY), ("already charged", ALREADY)])],
                                            *[cd[0].animate.set_stroke(GREY_D) for cd in cards], run_time=0.9),
                             Wait(1.6), FadeIn(c, shift=0.2 * RIGHT, run_time=0.6)), run_time=5.6)

        a = rep()
        heard = T("shop hears: A00001", 24, GREEN_M).move_to([SX, -0.75, 0])
        self.beat("Where the card was already charged, the issuer finds the key and sends back the stored answer, "
                  "without charging again. Where it wasn't, the retry charges it once.",
                  Succession(c.animate(run_time=1.0).move_to([LANE - 0.95, QC, 0]), FadeOut(c, run_time=0.3),
                             Transform(lines, iss("key pay-1: seen", "same code, no charge", GREEN_M), run_time=0.7), Wait(0.6),
                             FadeIn(a, run_time=0.3), a.animate(run_time=1.0).move_to([-LANE + 0.65, RC, 0]),
                             AnimationGroup(FadeOut(a), Transform(view, heard), run_time=0.6)), run_time=8.6)

        once = [T("charged once", 20, GREEN_M).move_to(cd[2]) for cd in cards]
        self.beat("One charge in every world, and now the shop knows the outcome.",
                  Succession(LaggedStart(*[Transform(cd[2], o) for cd, o in zip(cards, once)], lag_ratio=0.15, run_time=1.6),
                             Wait(0.4), Indicate(view, color=GREEN_M, run_time=1.0)), run_time=3.6)
        self.wait(0.6)
