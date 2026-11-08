from sfz import *

SAY.insert(0, (r"\bids\b", "I Ds"))
SAY.insert(0, (r"\bid\b", "I D"))

XS = [-5.45, -2.725, 0.0, 2.725, 5.45]           # phone, API server, broker, consumer, ledger
NAMES = ["phone", "API server", "broker", "consumer", "ledger"]
COLS = [BLUE_M, TEAL_M, PURPLE_M, TEAL_M, GOLD_M]
PY = 1.0                                         # the pipeline row
BW, BH = 2.1, 1.0
SUB_Y = PY - 0.82                                # a status line under each box
G_Y = -0.8                                       # guards
CAP_Y, CNT_Y, TOP, ID_Y = -1.95, -2.9, 3.2, 2.3


def glow(rect, color=YELLOW_M, s=1.05):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


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


def node(i):
    r = RoundedRectangle(corner_radius=0.14, width=BW, height=BH, stroke_color=COLS[i], stroke_width=3)
    r.set_fill(interpolate_color(ManimColor("#000000"), ManimColor(COLS[i]), 0.14), opacity=1).move_to([XS[i], PY, 0])
    return VGroup(r, T(NAMES[i], 26).move_to([XS[i], PY, 0]))


def sub(i, s, color=GREY_B):
    return T(s, 22, color).move_to([XS[i], SUB_Y, 0])


def guard(x, title, detail, color):
    a = T(title, 24, color).move_to([x, G_Y + 0.2, 0])
    b = T(detail, 20, GREY_B).move_to([x, G_Y - 0.2, 0])
    return VGroup(a, b)


def counter(rows, moved, color=WHITE):
    a = T(f"ledger rows: {rows}", 24, color)
    b = T(f"money moved: {moved}", 24, color)
    return VGroup(a, b).arrange(RIGHT, buff=0.8).move_to([0, CNT_Y, 0])


def caption(s, color=GREY_B, y=CAP_Y):
    return T(s, 24, color).move_to([0, y, 0])


class EndToEnd(Base):
    """derive-03, section 2: one transfer through phone, API server, broker, consumer and ledger. The reply is lost,
    the phone retries, TCP's and the broker's checks can't see it, and a request id made at the tap and enforced by a
    unique constraint at the ledger stops the second row."""

    def construct(self):
        self.title_card("The end-to-end argument", "a retried transfer, and where the duplicate is caught")

        nodes = [node(i) for i in range(5)]
        hops = [Arrow(nodes[i][0].get_right(), nodes[i + 1][0].get_left(), buff=0.08, stroke_width=3, color=GREY_B,
                      max_tip_length_to_length_ratio=0.3) for i in range(4)]
        s0 = sub(0, "taps send: 45.00", BLUE_M)
        self.steps("A customer on a train taps send to transfer 45 euros. "
                   "It goes to the API server, then through a broker to a consumer that writes the ledger.", [
            (lambda: [FadeIn(nodes[0], shift=0.2 * RIGHT)], 0.7),
            (lambda: [FadeIn(s0)], 0.5),
            "It goes to",
            (lambda: [GrowArrow(hops[0]), FadeIn(nodes[1])], 0.7),
            "then through",
            (lambda: [GrowArrow(hops[1]), FadeIn(nodes[2])], 0.7),
            "to a consumer",
            (lambda: [GrowArrow(hops[2]), FadeIn(nodes[3])], 0.6),
            "writes the ledger",
            (lambda: [GrowArrow(hops[3]), FadeIn(nodes[4])], 0.6),
        ])

        cnt = counter(1, "45.00")
        mid = (nodes[0][0].get_right() + nodes[1][0].get_left()) / 2
        lost_x = tick(False, 0.15).move_to(mid + 0.4 * UP)

        def run(color, rt=0.45):
            return [(lambda h=h: [travel(h, color, rt)], rt) for h in hops]

        def reply_dies():
            d = Dot(radius=0.08, color=WHITE).move_to(hops[0].get_end())
            return [Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(hops[0].get_end(), mid), run_time=0.4),
                               FadeOut(d, run_time=0.2))]

        self.steps("The transfer goes through, and the ledger gets one row. Then the reply is lost in a tunnel.", [
            *run(BLUE_M),
            (lambda: [FadeIn(cnt, shift=0.15 * UP)], 0.7),
            "Then the reply",
            (reply_dies, 0.65),
            (lambda: [Create(lost_x)], 0.5),
        ])

        s0b = sub(0, "no reply in 10 s", RED_M)
        self.steps("The phone can't tell a lost request from a lost reply. After 10 seconds it does the only safe thing, and sends it again.", [
            (lambda: [Transform(s0, s0b)], 0.7),
            "After 10 seconds",
            (lambda: [glow(nodes[0][0], BLUE_M)], 0.9),
            "and sends it again",
            (lambda: [Transform(s0, sub(0, "retry: 45.00", BLUE_M)), FadeOut(lost_x)], 0.6),
        ])

        cnt2 = counter(2, "90.00", RED_M)
        newc = caption("the retry: a new connection, a new request", RED_M)
        self.steps("The retry goes out on a new connection, and the server handles it as a new transfer. Now 90 euros have left the account.", [
            (lambda: [FadeIn(newc)], 0.6),
            *run(RED_M),
            "Now 90 euros",
            (lambda: [Transform(cnt, cnt2), nodes[4][0].animate.set_stroke(RED_M)], 0.8),
        ])

        g_tcp = guard((XS[0] + XS[1]) / 2, "TCP", "one connection only", TEAL_M)
        g_brk = guard(XS[2], "idempotent producer", "one producer's resends", PURPLE_M)
        self.steps("Each layer below has its own duplicate check. Look at what each one can see.", [
            (lambda: [FadeOut(newc), FadeIn(g_tcp, shift=0.15 * UP)], 0.8),
            (lambda: [FadeIn(g_brk, shift=0.15 * UP)], 0.8),
        ])

        c_tcp = caption("TCP: a new connection has fresh numbers, so the retry gets through", TEAL_M)
        fit(c_tcp, 12.6)
        self.steps("TCP drops a copy of bytes it has already delivered, but only on one connection. The retry came on a new one.", [
            (lambda: [Indicate(g_tcp[0], color=TEAL_M)], 0.9),
            "but only on one",
            (lambda: [Indicate(g_tcp[1], color=TEAL_M)], 0.9),
            "The retry came",
            (lambda: [FadeIn(c_tcp), travel(hops[0], RED_M, 0.6)], 0.8),
        ])

        c_brk = caption("broker: the retry was sent as a new record, with a new number", PURPLE_M)
        fit(c_brk, 12.6)
        self.steps("The broker drops a batch the producer resends with the same sequence number. The retry was a new request, so it got a new number.", [
            (lambda: [Indicate(g_brk[0], color=PURPLE_M)], 0.9),
            "The retry was",
            (lambda: [ReplacementTransform(c_tcp, c_brk), travel(hops[1], RED_M, 0.6)], 0.8),
        ])

        intent = T("the duplicate lives in what the customer meant: one tap, one transfer", 24, YELLOW_M).move_to([0, TOP, 0])
        fit(intent, 12.6)
        self.steps("Each check is right inside its own layer. The duplicate only exists in what the customer meant: one tap, one transfer.", [
            (lambda: [Indicate(g_tcp[0], color=GREEN_M), Indicate(g_brk[0], color=GREEN_M)], 1.0),
            "The duplicate",
            (lambda: [FadeOut(c_brk), FadeIn(intent, shift=0.15 * DOWN)], 0.9),
        ])

        idc = chip("id req-7f3a", YELLOW_M, 20, mono=True).move_to([XS[0], ID_Y, 0])
        self.steps("Only the phone knows that. So it makes an id when the user taps send, and puts the same id on every attempt.", [
            (lambda: [glow(nodes[0][0], BLUE_M)], 0.9),
            "So it makes",
            (lambda: [FadeIn(idc, shift=0.15 * DOWN)], 0.8),
            "and puts the same",
            (lambda: [Transform(s0, sub(0, "same id every time", YELLOW_M))], 0.7),
        ])

        carry = [chip(s, YELLOW_M, 18) for s in ("HTTP header", "record header", "record header", "id column")]
        for c, x in zip(carry, XS[1:]):
            c.move_to([x, ID_Y, 0])
        self.steps("Every hop carries it: an HTTP header, then a Kafka record header, then a column in the ledger row.", [
            "an HTTP header",
            (lambda: [FadeIn(carry[0], shift=0.15 * RIGHT)], 0.6),
            "then a Kafka",
            (lambda: [FadeIn(carry[1], shift=0.15 * RIGHT), FadeIn(carry[2], shift=0.15 * RIGHT)], 0.7),
            "then a column",
            (lambda: [FadeIn(carry[3], shift=0.15 * RIGHT)], 0.6),
        ])

        g_led = guard(XS[4] - 0.15, "unique request id", "same transaction", GREEN_M)
        self.steps("The ledger makes that column unique, and inserts the row in the same transaction that moves the money.", [
            (lambda: [FadeIn(g_led[0], shift=0.15 * UP)], 0.8),
            "and inserts",
            (lambda: [FadeIn(g_led[1], shift=0.15 * UP)], 0.8),
        ])

        ok = caption("insert finds req-7f3a already there: no row, no money", GREEN_M)
        cnt3 = counter(1, "45.00", GREEN_M)
        self.steps("Run the retry again. It reaches the ledger carrying the same id. The insert finds it already there and does nothing, so the money moves once.", [
            (lambda: [Transform(cnt, counter(1, "45.00")), nodes[4][0].animate.set_stroke(GOLD_M)], 0.6),
            "It reaches",
            *run(YELLOW_M, 0.4),
            "The insert finds",
            (lambda: [Indicate(g_led[0], color=GREEN_M), FadeIn(ok)], 0.9),
            "so the money",
            (lambda: [Transform(cnt, cnt3)], 0.7),
        ])

        self.steps("That's the end-to-end argument: a check like this is only complete at the ends. The layers below make the common case fast.", [
            "only complete at the ends",
            (lambda: [glow(nodes[0][0], BLUE_M), glow(nodes[4][0], GOLD_M)], 1.1),
            "The layers below",
            (lambda: [Indicate(g_tcp[0], color=TEAL_M), Indicate(g_brk[0], color=PURPLE_M)], 1.0),
        ])
        self.wait(0.6)
