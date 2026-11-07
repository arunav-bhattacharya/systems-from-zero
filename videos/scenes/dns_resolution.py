from sfz import *

SAY.insert(0, (r"(?<![\w.])\.com\b", "dot com"))
SAY.insert(0, (r"\bexample\.com\b", "example dot com"))
SAY.insert(0, (r"\bissuer\.example\.com\b", "issuer dot example dot com"))

def flash(m, color, s=1.08):
    """Indicate for solid-filled boxes: grow and recolour the outline, then back, so the label stays readable."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color)



class DnsResolution(VoiceScene):
    """net-09: stub resolver, recursive resolver, root, TLD, authoritative server, TTL, and the cache."""

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
        self.title_card("How a DNS lookup walks the tree", "and why the second lookup is instant")

        MID = 1.0
        q = chip("issuer.example.com ?", BLUE_M, size=18, mono=True).move_to([-4.9, 2.3, 0])
        stub = box("stub resolver", BLUE_M, size=26).move_to([-4.9, MID, 0])
        stub_c = T("in the payment service", 20, GREY_B).next_to(stub, DOWN, buff=0.15)
        rec = box("recursive resolver", TEAL_M, size=26).move_to([-0.9, MID, 0])

        TX = 4.5
        root = box("root", WHITE, size=26, w=2.8).move_to([TX, 2.65, 0])
        com = box(".com", WHITE, size=26, w=2.8).move_to([TX, MID, 0])
        auth = box("example.com", WHITE, size=26, w=2.8).move_to([TX, -0.65, 0])
        e1 = Line(root.get_bottom(), com.get_top(), color=GREY_D, stroke_width=2)
        e2 = Line(com.get_bottom(), auth.get_top(), color=GREY_D, stroke_width=2)
        tree = VGroup(e1, e2, root, com, auth)

        def leg(a, b):
            pa, pb = ends(a, b)
            d = (pb - pa) / np.linalg.norm(pb - pa)
            return Line(pa + 0.12 * d, pb - 0.12 * d, color=GREY_B, stroke_width=2.5)

        def ask(a, b, color=BLUE_M, back=GREEN_M, rt=1.0):
            ln = leg(a, b)
            return (ln, lambda: [travel(ln, color, run_time=rt)],
                    lambda: [travel(Line(ln.get_end(), ln.get_start()), back, run_time=rt)])

        self.beat("The payment service needs to call the card issuer at issuer.example.com. But a packet needs an IP address, not a name. Something has to look the name up.",
                  FadeIn(q, shift=0.2 * DOWN), run_time=1.4)

        l0, out0, back0 = ask(stub, rec)
        self.seq("The service asks the stub resolver, a small piece of code on its own machine. The stub does no searching. It forwards the question to a recursive resolver, and waits.",
                 ([FadeIn(stub), FadeIn(stub_c)], 0.8),
                 3.0,
                 ([FadeIn(rec), Create(l0)], 0.8),
                 (out0, 1.0))

        # the cache, empty for now
        cache_box = RoundedRectangle(corner_radius=0.12, width=7.8, height=1.75, stroke_color=TEAL_M, stroke_width=2)
        cache_box.move_to([-2.5, -2.525, 0])
        cache_t = T("resolver's cache", 22, TEAL_M).next_to(cache_box, UP, buff=0.12).align_to(cache_box, LEFT).shift(0.15 * RIGHT)
        empty = T("empty", 22, GREY_B).move_to(cache_box)
        l1, out1, back1 = ask(rec, root)
        self.seq("The recursive resolver does the searching. Its cache is empty, so it starts at the top of the tree, at a root server.",
                 ([Create(cache_box), FadeIn(cache_t), FadeIn(empty)], 0.8),
                 1.6,
                 ([FadeIn(tree)], 1.0),
                 ([Create(l1)], 0.5),
                 (out1, 1.0))

        def row(i, name, ans, ttl, color=WHITE):
            y = cache_box.get_top()[1] - 0.4 - i * 0.48
            a = M(name, 18, color).move_to([cache_box.get_left()[0] + 0.3, y, 0], aligned_edge=LEFT)
            b = M(ans, 18, color).move_to([cache_box.get_left()[0] + 3.3, y, 0], aligned_edge=LEFT)
            c = M(ttl, 18, GREY_B).move_to([cache_box.get_right()[0] - 0.3, y, 0], aligned_edge=RIGHT)
            return VGroup(a, b, c)

        r1 = row(0, "com", "a.gtld-servers.net", "2 days")
        self.seq("The root doesn't know the address. It knows who runs each top-level domain, and refers the resolver to the .com servers.",
                 ([flash(root, YELLOW_M)], 0.8),
                 1.8,
                 (back1, 1.0),
                 ([FadeOut(empty), FadeIn(r1, shift=0.2 * DOWN), l1.animate.set_opacity(0.3)], 0.8))

        l2, out2, back2 = ask(rec, com)
        r2 = row(1, "example.com", "ns1.example.com", "2 days")
        self.seq("A .com server knows who runs each name under .com. It refers the resolver to example.com's own servers.",
                 ([Create(l2)], 0.4),
                 (out2, 1.0),
                 1.2,
                 (back2, 1.0),
                 ([FadeIn(r2, shift=0.2 * DOWN), l2.animate.set_opacity(0.3)], 0.8))

        l3, out3, back3 = ask(rec, auth)
        rec_leaf = chip("issuer → 203.0.113.10", GOLD_M, size=18, mono=True).next_to(auth, DOWN, buff=0.35)
        leaf_e = Line(auth.get_bottom(), rec_leaf.get_top(), color=GREY_D, stroke_width=2)
        ttl = ValueTracker(300)
        r3 = row(2, "issuer.example.com", "203.0.113.10", "300 s", GOLD_M)
        num = always_redraw(lambda: M(f"{int(round(ttl.get_value()))} s", 18, GREY_B).move_to(
            [cache_box.get_right()[0] - 0.3, r3[2].get_y(), 0], aligned_edge=RIGHT))
        self.seq("Those are the authoritative servers. They hold the actual records. One answers with the address, and a time to live, or TTL, of 300 seconds: how long anyone may keep the answer.",
                 ([Create(l3)], 0.4),
                 (out3, 1.0),
                 ([Create(leaf_e), FadeIn(rec_leaf)], 0.8),
                 2.2,
                 (back3, 1.0),
                 ([FadeIn(VGroup(r3[0], r3[1]), shift=0.2 * DOWN), FadeIn(num), l3.animate.set_opacity(0.3)], 0.8))

        ans = chip("203.0.113.10", GREEN_M, size=22, mono=True).move_to(q)
        t60 = T("first lookup: about 60 ms", 22, GREY_B).move_to([-6.4, -0.3, 0], aligned_edge=LEFT)
        self.seq("The resolver hands the address back to the stub, and the payment service can connect. That took four round trips, here about 60 milliseconds.",
                 (back0, 1.0),
                 ([ReplacementTransform(q, ans)], 0.8),
                 2.0,
                 ([FadeIn(t60)], 0.8))

        self.beat("On the way, the resolver cached every answer, each with its own TTL.",
                  Indicate(VGroup(r1, r2, r3[:2], num), color=TEAL_M, scale_factor=1.04), run_time=1.6)

        t1 = T("next lookup: about 1 ms", 22, GREEN_M).move_to([-6.4, -0.8, 0], aligned_edge=LEFT)
        hit = SurroundingRectangle(VGroup(r3[0], num), color=GREEN_M, buff=0.13, corner_radius=0.06)
        hit.stretch_to_fit_height(0.38)
        self.seq("A second later, the next payment needs the same name. The resolver finds it in its cache and answers in about a millisecond. No trip up the tree.",
                 ([tree.animate.set_opacity(0.35), VGroup(l1, l2, l3).animate.set_opacity(0.12), rec_leaf.animate.set_opacity(0.35),
                   leaf_e.animate.set_opacity(0.35), ttl.animate.set_value(299)], 1.0),
                 1.2,
                 (out0, 0.6),
                 ([Create(hit)], 0.5),
                 (back0, 0.6),
                 ([FadeIn(t1)], 0.6))

        self.seq("The cached answer ages. When its 300 seconds run out, the resolver drops it. The next lookup goes straight to the example.com servers, because the resolver still knows who they are.",
                 ([FadeOut(hit), ttl.animate(rate_func=linear).set_value(0)], 3.0),
                 ([FadeOut(r3[:2]), FadeOut(num)], 0.6),
                 1.0,
                 ([auth.animate.set_opacity(1), l3.animate.set_opacity(1), Indicate(r2, color=WHITE)], 0.8),
                 (out3, 0.9),
                 (back3, 0.9),
                 (lambda: (ttl.set_value(300), [FadeIn(r3[:2]), FadeIn(num)])[1], 0.6))

        self.beat("That's why a DNS change is never instant. Until the old TTL runs out, resolvers keep handing out the old address.",
                  flash(rec, YELLOW_M), run_time=1.4)

        self.seq("So a lookup walks down the tree, from the root to .com to example.com, and every answer is cached for its TTL.",
                 ([l3.animate.set_opacity(0.3), tree.animate.set_opacity(1)], 0.6),
                 (lambda: [Succession(flash(root, YELLOW_M), flash(com, YELLOW_M), flash(auth, YELLOW_M))], 2.4))
        self.wait(0.6)
