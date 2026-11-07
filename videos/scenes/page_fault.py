from sfz import *

SAY.insert(0, (r"\b9-bit\b", "nine bit"))

def flash(m, color, s=1.08):
    """Indicate for solid-filled boxes: grow and recolour the outline, then back, so the label stays readable."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color)



class PageFault(VoiceScene):
    """os-06: a virtual address split into indices, the four-level walk, the TLB, then a page fault on first touch."""

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
        self.title_card("Virtual memory", "a page-table walk and a page fault")

        X = [-5.3, -2.65, 0.0, 2.65, 5.3]
        YH, YC, YB, YT = 3.15, 2.35, 1.8, -0.05      # header, index chips, bit labels, tables
        BW, BH = 2.2, 1.8

        # 1. one virtual address
        pn = M("0xffff42401", 46)
        off = M("234", 46)
        addr = VGroup(pn, off).arrange(RIGHT, buff=0.04).move_to([0, 0.9, 0])
        off.align_to(pn, DOWN)
        cap = T("a virtual address", 24, GREY_B).next_to(addr, UP, buff=0.4)
        self.beat("Every address a program uses is virtual. On every load and store, the hardware turns it into a place in physical RAM.",
                  FadeIn(cap), Write(addr), run_time=2.0)

        # 2. page number and offset
        b1 = Brace(pn, DOWN, buff=0.15, color=BLUE_M)
        b2 = Brace(off, DOWN, buff=0.15, color=GOLD_M)
        l1 = T("page number, 36 bits", 22, BLUE_M).next_to(b1, DOWN, buff=0.12)
        l2 = T("offset, 12 bits", 22, GOLD_M).next_to(b2, DOWN, buff=0.12)
        self.seq("Memory comes in pages of 4 KB. The low 12 bits are the offset inside the page. The other 36 bits name the page.",
                 ([off.animate.shift(0.5 * RIGHT).set_color(GOLD_M)], 0.6),
                 1.0,
                 ([GrowFromCenter(b2), FadeIn(l2)], 0.8),
                 1.2,
                 ([pn.animate.set_color(BLUE_M), GrowFromCenter(b1), FadeIn(l1)], 0.8))

        # 3. a flat table is too big; the page number splits into four 9-bit indices
        flat = T("68.7 billion pages × 8 bytes = 512 GB, for every process", 26, RED_M).move_to([0, -1.6, 0])
        flat_x = Line(flat.get_left(), flat.get_right(), color=RED_M, stroke_width=3)
        header = M("virtual address 0xffff42401234", 26).move_to([0, YH, 0])

        def ichip(txt, color):
            c = chip(txt, color, size=24, mono=True)
            c[0].stretch_to_fit_width(1.35)
            return c

        chips = VGroup(*[ichip(str(v), BLUE_M).move_to([X[i], YC, 0]) for i, v in enumerate([511, 509, 18, 1])])
        ochip = ichip("0x234", GOLD_M).move_to([X[4], YC, 0])
        bits = VGroup(*[T("9 bits", 18, GREY_B).move_to([X[i], YB, 0]) for i in range(4)], T("12 bits", 18, GREY_B).move_to([X[4], YB, 0]))
        self.seq("A flat table for all those pages would take 512 GB. So the table is a tree, and the page number splits into four 9-bit indices.",
                 ([FadeIn(flat)], 0.6),
                 1.6,
                 ([Create(flat_x)], 0.5),
                 0.6,
                 ([FadeOut(VGroup(flat, flat_x, b1, b2, l1, l2, cap)), ReplacementTransform(pn, chips), ReplacementTransform(off, ochip),
                   FadeIn(header), FadeIn(bits)], 1.4))

        # the tables
        def table(i, title, entry, color=WHITE):
            r = RoundedRectangle(corner_radius=0.12, width=BW, height=BH, stroke_color=color, stroke_width=2.5)
            r.set_fill(BLACK, 1)
            t = T(title, 24).move_to(r.get_top() + 0.35 * DOWN)
            s = T("512 entries" if i < 4 else "in RAM", 18, GREY_B).next_to(t, DOWN, buff=0.1)
            e = mbox(entry, GREY_B, w=1.85, h=0.48, size=20).move_to(r.get_bottom() + 0.45 * UP)
            return VGroup(r, t, s, e).move_to([X[i], YT, 0])

        tabs = [table(0, "root", "entry 511"), table(1, "level 1", "entry 509"), table(2, "level 2", "entry 18"),
                table(3, "level 3", "entry 1"), table(4, "frame", "0x4a1f3")]
        drop = [Arrow([X[i], YB - 0.18, 0], [X[i], YT + BH / 2, 0], buff=0.06, stroke_width=2.5, color=GREY_B,
                      max_tip_length_to_length_ratio=0.25) for i in range(5)]

        def link(i, color=YELLOW_M):
            e = tabs[i][3]
            return Arrow(e.get_right(), [tabs[i + 1][0].get_left()[0], e.get_y(), 0], buff=0.05, stroke_width=3, color=color,
                         max_tip_length_to_length_ratio=0.3)

        def pick(i, color=YELLOW_M):
            e = tabs[i][3]
            return [e[0].animate.set_stroke(color).set_fill(interpolate_color(ManimColor("#000000"), ManimColor(color), 0.18), 1),
                    Indicate(chips[i] if i < 4 else ochip, color=color)]

        links = [link(i) for i in range(4)]
        self.seq("The walk starts at the root table. Entry 511 points to a level 1 table.",
                 ([FadeIn(tabs[0]), GrowArrow(drop[0])], 0.8),
                 0.6,
                 (pick(0), 1.0),
                 ([GrowArrow(links[0]), FadeIn(tabs[1]), GrowArrow(drop[1])], 0.9))

        self.seq("Entry 509 there points to level 2, entry 18 to level 3, and entry 1 holds the frame number: where the page sits in RAM.",
                 (pick(1), 0.8),
                 ([GrowArrow(links[1]), FadeIn(tabs[2]), GrowArrow(drop[2])], 0.7),
                 0.3,
                 (pick(2), 0.8),
                 ([GrowArrow(links[2]), FadeIn(tabs[3]), GrowArrow(drop[3])], 0.7),
                 0.3,
                 (pick(3), 0.8),
                 ([GrowArrow(links[3]), FadeIn(tabs[4])], 0.8))

        header2 = M("virtual 0xffff42401234  →  physical 0x4a1f3234", 26).move_to([0, YH, 0])
        self.seq("Add the offset, and you have the physical byte.",
                 ([GrowArrow(drop[4]), Indicate(ochip, color=GOLD_M)], 0.8),
                 ([Transform(header, header2), tabs[4][3][0].animate.set_stroke(GOLD_M)], 1.0))

        # the TLB
        PY = -2.45
        tlb_r = RoundedRectangle(corner_radius=0.12, width=5.0, height=1.9, stroke_color=GREEN_M, stroke_width=2.5).move_to([-3.4, PY, 0])
        tlb_t = T("TLB", 22, GREEN_M).move_to(tlb_r.get_top() + 0.32 * DOWN)
        tlb_row = M("0xffff42401 → 0x4a1f3", 20).move_to(tlb_r.get_top() + 0.85 * DOWN)
        self.seq("Four extra reads on every access would be slow. So the CPU caches translations in the TLB: page in, frame out.",
                 ([*[flash(t[3], YELLOW_M) for t in tabs[:4]]], 1.4),
                 2.4,
                 ([Create(tlb_r), FadeIn(tlb_t)], 0.7),
                 ([FadeIn(tlb_row, shift=0.2 * DOWN)], 0.8))

        walk = VGroup(*tabs, *links, *drop)
        hit = tick(True, 0.18).next_to(tlb_row, RIGHT, buff=0.25)
        self.beat("The next access to this page hits the TLB and skips the walk.",
                  walk.animate.set_opacity(0.25), FadeIn(hit), Indicate(tlb_row, color=GREEN_M), run_time=1.4)

        # 9. mmap: a region, no entries, no RAM
        k_r = RoundedRectangle(corner_radius=0.12, width=5.0, height=1.9, stroke_color=GOLD_M, stroke_width=2.5).move_to([3.4, PY, 0])
        k_t = T("kernel: regions", 22, GOLD_M).move_to(k_r.get_top() + 0.32 * DOWN)
        k_row = M("0xffff48400000, 1 GB, rw", 20).move_to([k_r.get_left()[0] + 0.35, k_r.get_top()[1] - 0.85, 0], aligned_edge=LEFT)
        self.seq("Now the program asks mmap for one gigabyte. The kernel only writes down a region: these addresses are valid. No entries, no RAM yet.",
                 ([walk.animate.set_opacity(1), FadeOut(hit)], 0.6),
                 1.2,
                 ([Create(k_r), FadeIn(k_t)], 0.7),
                 ([FadeIn(k_row, shift=0.2 * DOWN)], 0.8))

        # 10. first touch: TLB miss, the walk finds an empty entry, page fault
        header3 = M("virtual address 0xffff48400000", 26).move_to([0, YH, 0])
        new_chips = VGroup(*[ichip(str(v), BLUE_M).move_to([X[i], YC, 0]) for i, v in enumerate([511, 509, 66, 0])])
        new_off = ichip("0x000", GOLD_M).move_to([X[4], YC, 0])
        miss_row = M("0xffff48400 → ?", 20, RED_M).move_to(tlb_row)
        miss = tick(False, 0.16).next_to(miss_row, RIGHT, buff=0.25)
        e66 = mbox("66: empty", RED_M, w=1.85, h=0.48, size=20).move_to(tabs[2][3])
        fault = Arrow(tabs[2][0].get_bottom() + 0.3 * RIGHT, k_r.get_corner(UL) + 0.5 * RIGHT, buff=0.1, stroke_width=3.5, color=RED_M,
                      max_tip_length_to_length_ratio=0.2)
        fault_l = T("page fault", 20, RED_M).next_to(fault.get_center(), LEFT, buff=0.35)
        self.seq("The program writes its first byte there. The TLB misses, and the walk finds entry 66 empty. The CPU raises a page fault: a jump into the kernel.",
                 ([Transform(header, header3), Transform(chips, new_chips), Transform(ochip, new_off),
                   *[tabs[i][3][0].animate.set_stroke(GREY_B).set_fill(BLACK, 1) for i in range(4)], tabs[4][3][0].animate.set_stroke(GREY_B)], 1.0),
                 0.6,
                 ([Transform(tlb_row, miss_row), FadeIn(miss)], 0.8),
                 0.4,
                 (lambda: pick(0), 0.6),
                 (lambda: pick(1), 0.6),
                 ([Transform(tabs[2][3], e66), VGroup(tabs[3], tabs[4], links[2], links[3], drop[3], drop[4]).animate.set_opacity(0.15)], 0.8),
                 0.6,
                 ([GrowArrow(fault), FadeIn(fault_l)], 0.9))

        # 11. the kernel checks the regions
        ok = tick(True, 0.16).next_to(k_row, RIGHT, buff=0.2)
        self.seq("The kernel finds the address inside the new region, so this is a valid first touch.",
                 ([Indicate(k_row, color=GOLD_M)], 1.0),
                 1.4,
                 ([FadeIn(ok)], 0.6))

        # 12. a zeroed frame, a new level 3 table, the entry filled in
        new_l3 = table(3, "level 3", "entry 0")
        new_fr = table(4, "new frame", "all zeros")
        e66b = mbox("entry 66", GREEN_M, w=1.85, h=0.48, size=20).move_to(tabs[2][3])
        e66b[0].set_fill(interpolate_color(ManimColor("#000000"), ManimColor(GREEN_M), 0.18), 1)
        new_l3[3][0].set_stroke(GREEN_M).set_fill(interpolate_color(ManimColor("#000000"), ManimColor(GREEN_M), 0.18), 1)
        self.seq("It takes a free frame, fills it with zeros, builds the missing level 3 table, and writes the frame's number in.",
                 ([FadeOut(VGroup(tabs[4], drop[4])), FadeIn(new_fr)], 0.9),
                 0.8,
                 ([FadeOut(tabs[3]), FadeIn(new_l3)], 0.8),
                 0.4,
                 ([Transform(tabs[2][3], e66b), links[2].animate.set_opacity(1).set_color(GREEN_M),
                   links[3].animate.set_opacity(1).set_color(GREEN_M), drop[3].animate.set_opacity(1)], 0.9))

        # 13. the store runs again; the TLB keeps the translation
        new_row = M("0xffff48400 → 0x51c02", 20).move_to(tlb_row)
        cost = M("this fault: about 1 µs", 20, GREY_B).move_to([k_r.get_x(), k_r.get_top()[1] - 1.42, 0])
        self.seq("The CPU runs the store again. Now the walk finds the frame, and the TLB keeps the translation. That fault took about a microsecond.",
                 ([FadeOut(fault), FadeOut(fault_l)], 0.5),
                 ([*[flash(e, YELLOW_M) for e in (tabs[0][3], tabs[1][3], tabs[2][3], new_l3[3])],
                   GrowArrow(drop[4].copy().set_opacity(1))], 1.2),
                 0.6,
                 ([Transform(tlb_row, new_row), FadeOut(miss)], 0.8),
                 1.4,
                 ([FadeIn(cost)], 0.7))

        # 14. demand paging
        total = M("1 GB ÷ 4 KB = 262,144 faults", 18, GOLD_M).move_to(cost)
        self.beat("Touching the whole gigabyte takes 262,144 faults like this. That's demand paging: the kernel hands out memory one page at a time, on first touch.",
                  ReplacementTransform(cost, total), FadeOut(ok), run_time=1.4)
        self.wait(0.6)
