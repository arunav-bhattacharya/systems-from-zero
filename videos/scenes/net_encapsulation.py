from sfz import *

SAY.insert(0, (r"\bexample\.com\b", "example dot com"))

def flash(m, color, s=1.08):
    """Indicate for solid-filled boxes: grow and recolour the outline, then back, so the label stays readable."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color)



class NetEncapsulation(VoiceScene):
    """net-01: one HTTP request wrapped by TCP, IP and Ethernet, carried over a link, unwrapped at the server."""

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
        self.title_card("From a URL to bytes on the wire", "one request, wrapped and unwrapped")

        ROWS = [2.1, 0.8, -0.5, -1.8]          # application, transport, internet, link
        RX = 3.9                                # right edge of the packet
        LX = -5.9                               # left edge of the layer names
        LAYERS = ["Application", "Transport", "Internet", "Link"]
        UNITS = ["message", "segment", "packet", "frame"]

        def blk(name, n, color, w):
            r = RoundedRectangle(corner_radius=0.1, width=w, height=0.95, stroke_color=color, stroke_width=3)
            r.set_fill(BLACK if ManimColor(color).to_hex().upper() == "#FFFFFF" else interpolate_color(ManimColor("#000000"), ManimColor(color), 0.14), opacity=1)
            t = VGroup(T(name, 22), M(f"{n} bytes", 17, GREY_B)).arrange(DOWN, buff=0.1).move_to(r)
            return VGroup(r, t)

        def place(blocks, row):
            g = VGroup(*[b.copy() for b in blocks])
            g.arrange(RIGHT, buff=0.06)
            g.move_to([RX - g.width / 2, ROWS[row], 0])
            return g

        def size_label(n, row):
            g = VGroup(M(f"{n} bytes", 22), T(UNITS[row], 22, GREY_B)).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
            return g.move_to([RX + 0.35 + g.width / 2, ROWS[row], 0])

        def inspector(line, color, y=-3.05, hl=None, hl_color=YELLOW_M):
            t = M(line, 20, color, t2c={hl: hl_color} if hl else None)
            fit(t, 12.6)
            return t.move_to([0, y, 0])

        def part(t, line, sub):
            i = line.replace(" ", "").find(sub.replace(" ", ""))
            return t[i:i + len(sub.replace(" ", ""))]

        # 1. the request itself
        req = VGroup(*[M(s, 22) for s in ["GET / HTTP/1.1", "Host: example.com", "User-Agent: curl/8.5.0", "Accept: */*"]])
        req.arrange(DOWN, aligned_edge=LEFT, buff=0.16)
        req_box = SurroundingRectangle(req, buff=0.3, corner_radius=0.12, color=WHITE, stroke_width=3)
        reqg = VGroup(req_box, req).move_to([0, 0.3, 0])
        req_n = M("74 bytes", 22, GREY_B).next_to(reqg, DOWN, buff=0.3)
        req_keep = reqg.copy()
        self.beat("Curl wants the home page of example.com. It writes a request of 74 bytes: a GET line and three header lines.",
                  FadeIn(reqg, shift=0.2 * UP), FadeIn(req_n), run_time=2.0)

        # 2. the stack appears, the request becomes the application-layer block
        labels = VGroup(*[T(n, 26, GREY_B).move_to([LX, y, 0], aligned_edge=LEFT) for n, y in zip(LAYERS, ROWS)])
        labels[0].set_color(WHITE)
        where = T("your machine", 24, GREY_B).move_to([LX, 3.15, 0], aligned_edge=LEFT)
        http = blk("HTTP request", 74, WHITE, 2.7)
        http.move_to(place([http], 0)[0])
        pkt = VGroup(http)
        sz = size_label(74, 0)
        self.beat("The kernel carries those bytes down four layers. Each layer puts its own header in front.",
                  FadeIn(where), LaggedStart(*[FadeIn(l, shift=0.2 * RIGHT) for l in labels], lag_ratio=0.2),
                  ReplacementTransform(VGroup(reqg, req_n), VGroup(http)), FadeIn(sz), run_time=2.6)

        def wrap(new, row, total):
            target = place([new] + list(pkt), row)
            new.move_to(target[0])
            moves = [m.animate.move_to(t.get_center()) for m, t in zip(list(pkt), list(target[1:]))]
            return [*moves, FadeIn(new, shift=0.6 * RIGHT), Transform(sz, size_label(total, row)),
                    labels[row - 1].animate.set_color(GREY_B), labels[row].animate.set_color(WHITE)]

        # 3. TCP
        tcp = blk("TCP", 32, BLUE_M, 1.75)
        ins = inspector("TCP header: ports 57236 → 80, sequence numbers, flags", BLUE_M)
        self.beat("TCP adds 32 bytes: the two ports, which pick the program at each end, and numbers that keep the bytes in order. Now it's 106 bytes, a segment.",
                  *wrap(tcp, 1, 106), FadeIn(ins), run_time=2.2)
        pkt = VGroup(tcp, *pkt)

        # 4. IP
        ip = blk("IP", 20, GREEN_M, 1.5)
        ins2 = inspector("IP header: 172.20.0.2 → 104.20.23.154, TTL 64, protocol 6", GREEN_M)
        self.beat("IP adds 20 bytes: the two IP addresses, which pick the machine, and a time to live counter. Now 126 bytes, a packet.",
                  *wrap(ip, 2, 126), Transform(ins, ins2), run_time=2.2)
        pkt = VGroup(ip, *pkt)

        # 5. Ethernet
        eth = blk("Ethernet", 14, GOLD_M, 1.6)
        ETH_LINE = "Ethernet header: b6:99:4a:b0:80:7f → 22:d2:d5:a2:32:a3, type 0x0800"
        ins3 = inspector(ETH_LINE, GOLD_M, hl="22:d2:d5:a2:32:a3")
        self.beat("Ethernet adds 14: the two MAC addresses, which pick the network card on this one link, and a type field. 140 bytes, a frame.",
                  *wrap(eth, 3, 140), FadeOut(ins), FadeIn(ins3), run_time=2.2)
        ins = ins3
        pkt = VGroup(eth, *pkt)

        # 6. encapsulation: each layer's payload is everything above it
        br = Brace(VGroup(ip, tcp, http), UP, buff=0.12, color=GOLD_M)
        br_l = T("Ethernet's payload: it never looks inside", 22, GOLD_M).next_to(br, UP, buff=0.12)
        self.beat("This is encapsulation. Each layer wraps what the layer above handed it, and never looks inside.",
                  GrowFromCenter(br), FadeIn(br_l), run_time=1.6)

        # 7. the link: your machine, a router, the server
        self.play(FadeOut(br), FadeOut(br_l), FadeOut(labels), FadeOut(where), FadeOut(sz), run_time=0.6)
        MY = 1.7
        me = box("your machine", WHITE, size=24).move_to([-4.9, MY, 0])
        rt_ = box("router", WHITE, size=24).move_to([0, MY, 0])
        srv = box("server", WHITE, size=24).move_to([4.9, MY, 0])
        l1 = Line(me.get_right(), rt_.get_left(), color=GREY_B, stroke_width=2.5)
        l2 = Line(rt_.get_right(), srv.get_left(), color=GREY_B, stroke_width=2.5)
        mac_me = M("b6:99:4a:b0:80:7f", 16, GREY_B).next_to(me, DOWN, buff=0.18)
        mac_rt = M("22:d2:d5:a2:32:a3", 16, YELLOW_M).next_to(rt_, DOWN, buff=0.18)
        net = VGroup(l1, l2, me, rt_, srv)
        self.play(FadeIn(net), pkt.animate.move_to([0, -0.55, 0]), ins.animate.move_to([0, -1.85, 0]), run_time=1.0)

        def hop(line, color=GOLD_M):
            return travel(line, color, run_time=1.2)

        self.seq("The destination MAC is the router's, the next card on your link. So the frame crosses one cable, to the router.",
                 ([FadeIn(mac_me), FadeIn(mac_rt)], 0.8),
                 ([Indicate(part(ins, ETH_LINE, "22:d2:d5:a2:32:a3"), color=WHITE, scale_factor=1.0), Indicate(mac_rt, color=YELLOW_M)], 1.4),
                 0.6,
                 ([hop(l1)], 1.4),
                 ([flash(rt_, GOLD_M)], 0.8))

        # 8. the router takes off the Ethernet header and lowers the TTL
        eth_pos = eth.get_center()
        ins_r = inspector("router reads: to 104.20.23.154, TTL 64 → 63", GREEN_M, y=-1.85)
        self.seq("The router strips the Ethernet header, reads the destination IP address, and lowers the time to live from 64 to 63.",
                 ([eth.animate.shift(0.9 * UP).set_opacity(0)], 1.0),
                 ([Transform(ins, ins_r), flash(ip, GREEN_M)], 1.4))
        self.remove(eth)

        # 9. a new Ethernet header for the next link
        eth2 = blk("Ethernet", 14, PURPLE_M, 1.6).move_to(eth_pos).shift(0.9 * UP)
        eth2.set_opacity(0)
        ins_n = inspector("new Ethernet header: 22:d2:d5:a2:32:a3 → the next card, type 0x0800", PURPLE_M, y=-1.85)
        self.seq("Then it wraps the packet in a new Ethernet header for the next link. MAC addresses change at every hop. IP addresses and ports don't.",
                 ([eth2.animate.shift(0.9 * DOWN).set_opacity(1)], 1.0),
                 ([Transform(ins, ins_n)], 0.6),
                 1.6,
                 ([hop(l2, PURPLE_M)], 1.4),
                 ([flash(VGroup(ip, tcp), YELLOW_M, 1.05)], 1.0))
        eth = eth2
        pkt = VGroup(eth, ip, tcp, http)

        # 10. at the server: the same steps, backwards
        where2 = T("the server", 24, GREY_B).move_to([LX, 3.15, 0], aligned_edge=LEFT)
        for l in labels:
            l.set_color(GREY_B)
        labels[3].set_color(WHITE)
        sz = size_label(140, 3)
        target = place(list(pkt), 3)
        self.play(FadeOut(net), FadeOut(mac_me), FadeOut(mac_rt), FadeOut(ins), run_time=0.6)
        self.beat("At the server, the kernel runs the same steps backwards. Each header says what is inside it.",
                  pkt.animate.move_to(target.get_center()), FadeIn(where2), FadeIn(labels), FadeIn(sz), run_time=1.6)

        def unwrap(outer, rest, row, total, line, color, swap_out=None):
            # Steps are built lazily: two .animate builders on one mobject made up front would share a target.
            new_ins = inspector(line, color)

            def read():
                return [flash(outer, YELLOW_M), FadeIn(new_ins)] + ([FadeOut(swap_out)] if swap_out else [])

            def strip():
                return [outer.animate.shift(0.8 * LEFT).set_opacity(0)]

            def rise():
                target = place(list(rest), row)
                return [*[m.animate.move_to(t.get_center()) for m, t in zip(list(rest), list(target))],
                        Transform(sz, size_label(total, row)), labels[row + 1].animate.set_color(GREY_B),
                        labels[row].animate.set_color(WHITE)]

            return [(read, 1.2), (strip, 0.7), (rise, 0.9)], new_ins

        steps, ins = unwrap(eth, [ip, tcp, http], 2, 126, "type 0x0800: an IPv4 packet is inside", PURPLE_M)
        self.seq("The Ethernet type field says an IP packet follows. Off comes the Ethernet header.", *steps)
        self.remove(eth)

        steps, ins2 = unwrap(ip, [tcp, http], 1, 106, "protocol 6: a TCP segment is inside", GREEN_M, swap_out=ins)
        self.seq("The IP protocol number, 6, says a TCP segment follows. Off comes the IP header.", *steps)
        self.remove(ip)
        ins = ins2

        steps, ins2 = unwrap(tcp, [http], 0, 74, "port 80: the web server", BLUE_M, swap_out=ins)
        self.seq("The TCP port, 80, picks the web server. It reads exactly the 74 bytes curl wrote.", *steps)
        self.remove(tcp)
        ins = ins2

        # 14. the one sentence to keep
        req2 = req_keep
        req2_n = M("74 bytes, as curl wrote them", 22, GREY_B).next_to(req2, DOWN, buff=0.3)
        self.beat("On the way down, each layer adds a header. On the way up, each layer reads one and removes it. Routers touch only the outermost one.",
                  FadeTransform(http, req2), FadeIn(req2_n), FadeOut(ins), FadeOut(labels), FadeOut(where2), FadeOut(sz), run_time=1.6)
        self.wait(0.6)
