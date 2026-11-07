from sfz import *

SAY.insert(0, (r"\bTIME_WAIT\b", "time wait"))


class TcpHandshake(VoiceScene):
    """net-07: SYN, SYN-ACK, ACK with sequence numbers, data and its ACK, the four-way close, and TIME_WAIT."""

    def seq(self, text, *steps, after=0.25):
        """Speak one line and play several animation steps inside it. A step is (anims or a function
        returning anims, run_time), or a number of seconds to wait."""
        path, dur = voice(text)
        self._cue(text, dur)
        self.add_sound(path)
        used = 0.0
        for st in steps:
            if isinstance(st, (int, float)):
                self.wait(st)
                used += st
                continue
            anims, rt = st
            anims = anims() if callable(anims) else anims
            self.play(*anims, run_time=rt)
            used += rt
        if used > dur + 0.05:
            print(f"WARNING: steps {used:.1f}s longer than line {dur:.1f}s: {text[:40]}")
        if dur - used > 0.02:
            self.wait(dur - used)
        if after:
            self.wait(after)

    def construct(self):
        self.title_card("The TCP handshake", "sequence numbers, the close, and TIME_WAIT")

        XC, XS = -3.7, 3.7
        TOP = 2.85
        cli = box("payment service", BLUE_M, size=26).move_to([XC, TOP, 0])
        srv = box("ledger", GOLD_M, size=26, w=2.6).move_to([XS, TOP, 0])
        lc = Line([XC, TOP - 0.45, 0], [XC, -3.35, 0], color=GREY_D, stroke_width=2.5)
        ls = Line([XS, TOP - 0.45, 0], [XS, -3.35, 0], color=GREY_D, stroke_width=2.5)

        Y0, STEP, DROP = 1.9, 0.95, 0.4

        def msg(slot, to_server, label, color, dashed=False):
            y = Y0 - slot * STEP
            a, b = (XC, XS) if to_server else (XS, XC)
            p0, p1 = np.array([a, y, 0]), np.array([b, y - DROP, 0])
            if dashed:
                ar = DashedLine(p0, p1, buff=0.06, dash_length=0.14, stroke_width=3.5, color=color)
                ar.add_tip(tip_length=0.26, tip_width=0.2)
            else:
                ar = Arrow(p0, p1, buff=0.06, stroke_width=3.5, color=color, max_tip_length_to_length_ratio=0.035,
                           max_stroke_width_to_length_ratio=10)
            lab = M(label, 22, color).move_to([0, y - DROP / 2 + 0.3, 0])
            return VGroup(ar, lab)

        def send(m, rt=1.0):
            return [GrowArrow(m[0]) if isinstance(m[0], Arrow) else Create(m[0]), FadeIn(m[1], shift=0.1 * DOWN)]

        self.beat("TCP numbers every byte it sends, so the receiver can put bytes in order and spot gaps. But first, both sides must agree where the numbers start.",
                  FadeIn(cli), FadeIn(srv), Create(lc), Create(ls), run_time=2.0)

        syn = msg(0, True, "SYN  seq 1000", TEAL_M)
        self.beat("The payment service picks a random starting number, say 1,000, and sends a SYN, short for synchronize.",
                  *send(syn), run_time=2.0)

        synack = msg(1, False, "SYN-ACK  seq 5000  ack 1001", TEAL_M)
        ack_part = synack[1][-7:]
        self.seq("The ledger picks its own, 5,000, and replies with a SYN-ACK. It acknowledges 1,001, the next byte it expects.",
                 (send(synack), 2.0),
                 1.2,
                 ([Indicate(ack_part, color=YELLOW_M, scale_factor=1.3)], 1.4))

        ack = msg(2, True, "ACK  ack 5001", GREEN_M)
        rt_line = Line([XC - 0.2, Y0, 0], [XC - 0.2, Y0 - STEP - DROP, 0])
        br = Brace(rt_line, LEFT, buff=0.05, color=GREY_B)
        br_l = T("one round trip", 22, GREY_B).next_to(br, LEFT, buff=0.15)
        self.seq("The client acknowledges 5,001. Now both sides know both starting numbers. That took one round trip, and no data has moved yet.",
                 (send(ack), 1.4),
                 2.0,
                 ([GrowFromCenter(br), FadeIn(br_l)], 1.0))

        data = msg(3, True, "seq 1001  100 bytes", YELLOW_M)
        self.beat("Now the client sends a 100-byte payment authorization. Its bytes are numbered 1,001 to 1,100.",
                  *send(data), run_time=1.8)

        dack = msg(4, False, "ACK  ack 1101", GREEN_M)
        self.beat("The ledger's kernel acknowledges 1,101: everything up to 1,100 has arrived. Without that, the client would send the bytes again.",
                  *send(dack), run_time=1.8)

        # the close: clear the board, keep the two machines
        old = VGroup(syn, synack, ack, data, dack, br, br_l)
        fin1 = msg(0, True, "FIN  seq 1101", RED_M)
        self.seq("To close, each side sends a FIN, short for finish, and the other side acknowledges it. The client finishes first.",
                 ([FadeOut(old, shift=0.4 * UP)], 0.8),
                 2.6,
                 (send(fin1), 1.4))

        ack2 = msg(1, False, "ACK  ack 1102", GREEN_M)
        fin2 = msg(2, False, "FIN  seq 5001", RED_M)
        self.seq("The ledger acknowledges it, then sends its own FIN.",
                 (send(ack2), 1.1),
                 (send(fin2), 1.1))

        ack3 = msg(3, True, "ACK  ack 5002", GREEN_M)
        closed = chip("CLOSED", GREY_B, size=20, mono=True).move_to([5.25, Y0 - 3 * STEP - DROP, 0])
        self.seq("The client acknowledges that, and the ledger closes the connection.",
                 (send(ack3), 1.3),
                 ([FadeIn(closed), ls.animate.set_opacity(0.35)], 0.7))

        tw = chip("TIME_WAIT", YELLOW_M, size=22, mono=True).move_to([-5.3, Y0 - 3 * STEP - DROP, 0])
        tw_l = T("60 s on Linux", 22, GREY_B).next_to(tw, DOWN, buff=0.18)
        self.beat("The client doesn't close yet. It waits in a state called TIME_WAIT, for 60 seconds on Linux. There are two reasons.",
                  FadeIn(tw, scale=1.2), FadeIn(tw_l), run_time=1.6)

        # reason 1: the last ACK may be lost
        cut = ack3[0].get_start() + 0.74 * (ack3[0].get_end() - ack3[0].get_start())
        lost = tick(False, 0.24).move_to(cut)
        lost_line = Line(ack3[0].get_start(), cut, color=RED_M, stroke_width=3.5)
        fin_again = msg(4, False, "FIN  seq 5001  (again)", RED_M, dashed=True)
        ack_again = msg(5, True, "ACK  ack 5002", GREEN_M)
        self.seq("First, the client's last message might be lost. The ledger would then send its FIN again, and the client must still be there to answer it.",
                 ([VGroup(fin1, ack2, fin2).animate.set_opacity(0.3), Transform(ack3[0], lost_line), ack3[1].animate.set_color(RED_M), FadeIn(lost, scale=1.4),
                   closed.animate.set_opacity(0), ls.animate.set_opacity(1)], 1.0),
                 1.4,
                 (send(fin_again), 1.3),
                 1.0,
                 (send(ack_again), 1.2),
                 ([Indicate(tw, color=YELLOW_M)], 0.9))

        # reason 2: a late copy of an old packet
        stray = chip("late copy:  seq 1001", YELLOW_M, size=20, mono=True).move_to([-1.0, -0.2, 0])
        path = ArcBetweenPoints(np.array([-1.0, -0.2, 0]), np.array([1.6, -1.1, 0]), angle=0.6)
        self.seq("Second, a late copy of an old packet may still be in the network. It must not land in a new connection on the same ports. Waiting lets it die first.",
                 ([FadeOut(VGroup(fin1, ack2, fin2, ack3, lost, fin_again, ack_again))], 0.8),
                 ([FadeIn(stray, scale=0.8)], 0.8),
                 ([MoveAlongPath(stray, path)], 3.4),
                 1.2,
                 ([stray.animate.set_opacity(0).scale(0.7)], 1.2),
                 ([Indicate(tw, color=YELLOW_M)], 0.9))

        # the cost: every port the client used sits in TIME_WAIT for a minute
        bar = Rectangle(width=6.4, height=0.55, stroke_color=GREY_B, stroke_width=2.5).move_to([0, -0.6, 0])
        bar_t = T("28,232 client ports, from 32768 to 60999", 20, GREY_B).next_to(bar, UP, buff=0.25)
        fill = Rectangle(width=6.4, height=0.55, stroke_width=0).set_fill(YELLOW_M, 0.55).move_to(bar)
        fill.stretch(0.001, 0, about_edge=LEFT)
        fill_t = T("470 new connections a second fill every port", 20, YELLOW_M).next_to(bar, DOWN, buff=0.25)
        self.seq("Only the side that closes first waits. A Linux client has about 28,000 ports, so more than 470 new connections a second to one server runs out of them.",
                 ([FadeIn(bar), FadeIn(bar_t), FadeIn(fill)], 0.8),
                 2.0,
                 ([fill.animate.stretch(1000, 0, about_edge=LEFT), FadeIn(fill_t)], 3.6))

        fill_t2 = T("a pool: a few connections, reused", 20, GREEN_M).next_to(bar, DOWN, buff=0.25)
        self.beat("Keep connections open and reuse them, and you pay for the handshake and the wait only once.",
                  fill.animate.stretch(0.035, 0, about_edge=LEFT).set_fill(GREEN_M, 0.7),
                  ReplacementTransform(fill_t, fill_t2), run_time=1.8)
        self.wait(0.6)
