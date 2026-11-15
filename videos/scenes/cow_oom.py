from sfz import *

SAY.insert(0, (r"\bSIGKILL\b", "sig kill"))
SAY.insert(0, (r"\bOOM\b", "O O M"))

TX, TW, TH = 4.95, 3.0, 3.2            # page tables: centre x (±), width, height
FX, FW, FH = 1.12, 2.0, 0.6            # RAM frames: sub-column x (±), width, height
TOP, BOT = 1.65, -1.55                 # top and bottom of the tables and the RAM column
ROWS = [0.7, -0.1, -0.9]               # page 0, 1, 2
X0, U = -4.6, 1.15                     # the memory bars: left edge, units per GB
PR_Y, RAM_Y, BH = 1.0, -0.6, 0.62      # promised row, in-RAM row, bar height
CAP_X = X0 + 8 * U                     # 8 GB


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


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
        if t > dur + 0.1:
            print(f"WARNING: steps {t:.1f}s longer than line {dur:.1f}s: {text[:50]}")
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)


def arr(a, b, color=GREY_B, sw=2.5):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    n = np.linalg.norm(b - a)
    return Arrow(a, b, buff=0.04, stroke_width=sw, color=color, max_tip_length_to_length_ratio=0.2 / n,
                 max_stroke_width_to_length_ratio=20)


def table(x, title):
    r = RoundedRectangle(corner_radius=0.14, width=TW, height=TH, stroke_color=WHITE, stroke_width=2.5).set_fill(BLACK, 1)
    r.move_to([x, (TOP + BOT) / 2, 0])
    return VGroup(r, T(title, 22, GREY_B).move_to([x, TOP - 0.33, 0]))


def entry(x, k, perm="writable", pcolor=GREEN_M):
    y = ROWS[k]
    r = RoundedRectangle(corner_radius=0.08, width=TW - 0.4, height=0.5, stroke_color=GREY_B, stroke_width=2).set_fill(BLACK, 1)
    r.move_to([x, y, 0])
    return VGroup(r, left_at(M(f"page {k}", 18), x - TW / 2 + 0.38, y), perm_t(x, k, perm, pcolor))


def perm_t(x, k, perm, pcolor):
    return right_at(T(perm, 17, pcolor), x + TW / 2 - 0.38, ROWS[k])


def frame(side, k, name, count, color=WHITE):
    x, y = side * FX, ROWS[k]
    r = RoundedRectangle(corner_radius=0.08, width=FW, height=FH, stroke_color=color, stroke_width=2.5).set_fill(fillc(color), 1)
    r.move_to([x, y, 0])
    return VGroup(r, left_at(T(name, 18), x - FW / 2 + 0.16, y), cnt_t(side, k, count))


def cnt_t(side, k, count, color=GREY_B):
    return right_at(T(count, 15, color), side * FX + FW / 2 - 0.13, ROWS[k])


def p_arrow(k, color=GREY_B):
    """Parent's entry k to frame k (left sub-column)."""
    return arr([-TX + (TW - 0.4) / 2, ROWS[k], 0], [-FX - FW / 2, ROWS[k], 0], color)


def c_arrow(k, side, color=GREY_B):
    """Child's entry k to the frame in row k, in the left (-1) or right (+1) sub-column."""
    return arr([TX - (TW - 0.4) / 2, ROWS[k], 0], [side * FX + FW / 2, ROWS[k], 0], color)


def seg(a, b, y, color, label=None, size=17, op=0.32):
    """A bar segment from a GB to b GB on row y."""
    r = Rectangle(width=max((b - a) * U, 0.001), height=BH, stroke_color=color, stroke_width=2).set_fill(color, op)
    r.move_to([X0 + (a + b) / 2 * U, y, 0])
    g = VGroup(r)
    if label:
        g.add(T(label, size).move_to(r))
    return g


class CowOom(Base):
    """os-07, section 0 (with sections 2 and 3): fork of a 512 MB process shares frames; copy-everything would need a second
    512 MB. The kernel marks every entry read-only; the child's first write to page 1 faults and the kernel copies that one
    page (about 2 µs). Honest bookkeeping refuses a 4 GB JVM's fork on an 8 GB machine, so Linux overcommits (100 GB returns
    at once). A batch job touches its promise until RAM is full; reclaim drops the file cache; the OOM killer kills the
    biggest process, the JVM, although the batch job asked for the last page."""

    def construct(self):
        self.title_card("Copy-on-write and the OOM killer", "fork shares pages, and the kernel promises more than it has")

        # ---- 1. the parent ---------------------------------------------------------------------------------------
        pt = table(-TX, "parent's page table")
        pe = [entry(-TX, k) for k in range(3)]
        ram = RoundedRectangle(corner_radius=0.14, width=2 * FX + FW + 0.4, height=TH, stroke_color=GREY_B, stroke_width=2.5)
        ram.set_fill(BLACK, 1).move_to([0, (TOP + BOT) / 2, 0])
        ram_t = T("RAM", 22, GREY_B).move_to([0, TOP - 0.33, 0])
        fr = [frame(-1, k, f"frame {'ABC'[k]}", "1 map") for k in range(3)]
        pa = [p_arrow(k) for k in range(3)]
        note = T("3 of its 131,072 pages", 20, GREY_B).move_to([-TX, 2.3, 0])
        self.steps("A process holds 512 MB of memory, in pages of 4 KB. Its page table maps each page to a frame of RAM.", [
            (lambda: [FadeIn(pt), *[FadeIn(e) for e in pe]], 0.8),
            (lambda: [FadeIn(note, shift=0.1 * DOWN)], 0.5),
            "Its page table",
            (lambda: [FadeIn(ram), FadeIn(ram_t), *[FadeIn(f) for f in fr]], 0.8),
            (lambda: [*[GrowArrow(a) for a in pa]], 0.7),
        ])

        # ---- 2. fork: the child is running in 1.7 ms -------------------------------------------------------------
        ct = table(TX, "child's page table")
        q = T("?", 60, GREY_C).move_to([TX, ROWS[1], 0])
        cap1 = left_at(T("fork: the child runs 1.7 ms later", 21, TEAL_M), -6.4, -2.3)
        cap2 = left_at(T("copying 512 MB: 33 ms", 21, GREY_B), -6.4, -2.85)
        self.steps("It calls fork, and the child is running 1.7 milliseconds later. Copying 512 MB would take 33.", [
            (lambda: [FadeIn(ct), FadeIn(q)], 0.8),
            (lambda: [FadeIn(cap1, shift=0.1 * UP)], 0.6),
            "Copying",
            (lambda: [FadeIn(cap2, shift=0.1 * UP)], 0.6),
        ])

        # ---- 3. the simplest fork copies everything --------------------------------------------------------------
        cp = [frame(1, k, f"frame {'DEF'[k]}", "1 map", GREY_B) for k in range(3)]
        ce = [entry(TX, k) for k in range(3)]
        ca = [c_arrow(k, 1) for k in range(3)]
        cap3 = left_at(T("copy everything: RAM used 1,024 MB", 21, RED_M), -6.4, -2.85)
        self.steps("And copying every page would need a second 512 MB of RAM.", [
            (lambda: [FadeOut(q), *[travel(Line(fr[k].get_center(), cp[k].get_center()), YELLOW_M, 0.7) for k in range(3)]], 0.8),
            (lambda: [*[FadeIn(c, scale=0.9) for c in cp], *[FadeIn(e) for e in ce], *[GrowArrow(a) for a in ca]], 0.6),
            "a second",
            (lambda: [FadeOut(cap2), FadeIn(cap3, shift=0.1 * UP)], 0.6),
        ])

        # ---- 4. share instead ------------------------------------------------------------------------------------
        sa = [c_arrow(k, -1) for k in range(3)]
        cap5 = left_at(T("share: about 1 MB of new page table", 21, GREEN_M), -6.4, -2.85)
        self.steps("Instead, the child gets its own page table, pointing at the parent's frames. That's about 1 MB of table.", [
            (lambda: [FadeOut(cap3), *[FadeOut(c) for c in cp]], 0.6),
            "pointing at",
            (lambda: [*[ReplacementTransform(ca[k], sa[k]) for k in range(3)]], 0.9),
            (lambda: [*[Transform(fr[k][2], cnt_t(-1, k, "2 maps", TEAL_M)) for k in range(3)]], 0.5),
            "That's about",
            (lambda: [FadeIn(cap5, shift=0.1 * UP)], 0.6),
        ])

        # ---- 5. but a write would leak into the child -------------------------------------------------------------
        bad = tick(False, 0.2).move_to([TX, -1.3, 0])
        self.steps("But then a write by the parent would show up in the child.", [
            (lambda: [FadeOut(cap1), FadeOut(cap5), FadeOut(note)], 0.4),
            (lambda: [travel(Line(pa[1].get_start(), pa[1].get_end()), RED_M, 0.6)], 0.6),
            (lambda: [fr[1][0].animate.set_stroke(RED_M), sa[1].animate.set_color(RED_M)], 0.4),
            "show up",
            (lambda: [travel(Line(sa[1].get_end(), sa[1].get_start()), RED_M, 0.6), ce[1][0].animate.set_stroke(RED_M)], 0.6),
            (lambda: [Create(bad)], 0.4),
        ])

        # ---- 6. read-only in both tables --------------------------------------------------------------------------
        rule = T("at fork: every entry read-only", 22, GOLD_M).move_to([0, 2.3, 0])
        self.steps("So the kernel marks every entry read-only, in both tables. Reads still work.", [
            (lambda: [FadeOut(bad), fr[1][0].animate.set_stroke(WHITE), sa[1].animate.set_color(GREY_B),
                      ce[1][0].animate.set_stroke(GREY_B)], 0.5),
            (lambda: [FadeIn(rule, shift=0.1 * DOWN),
                      *[Transform(e[2], perm_t(-TX, k, "read-only", GOLD_M)) for k, e in enumerate(pe)],
                      *[Transform(e[2], perm_t(TX, k, "read-only", GOLD_M)) for k, e in enumerate(ce)]], 0.9),
            "Reads still",
            (lambda: [travel(Line(pa[0].get_start(), pa[0].get_end()), GREEN_M, 0.6),
                      travel(Line(sa[2].get_start(), sa[2].get_end()), GREEN_M, 0.8)], 0.8),
        ])

        # ---- 7. the child writes: page fault ----------------------------------------------------------------------
        kern = RoundedRectangle(corner_radius=0.12, width=4.4, height=0.72, stroke_color=GOLD_M, stroke_width=2.5)
        kern.set_fill(fillc(GOLD_M), 1).move_to([0, -2.5, 0])
        kt = T("kernel: page fault on page 1", 20).move_to(kern)
        fa = arr([TX - 0.6, BOT - 0.05, 0], [kern.get_right()[0] + 0.05, kern.get_y(), 0], RED_M, 3)
        fl = T("page fault", 19, RED_M).move_to([TX + 0.4, -2.25, 0])
        stop = Line(sa[1].get_start(), sa[1].get_start() + 0.8 * LEFT)

        def halt():
            d = Dot(radius=0.08, color=RED_M).move_to(stop.get_start())
            return [Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, stop, run_time=0.5), FadeOut(d, run_time=0.25))]

        self.steps("When the child writes page 1, the CPU refuses, and faults into the kernel.", [
            (lambda: [glow(ce[1][0], YELLOW_M, 1.04)], 0.6),
            "the CPU refuses",
            (lambda: halt(), 0.8),
            "and faults",
            (lambda: [GrowArrow(fa), FadeIn(fl)], 0.5),
            (lambda: [FadeIn(kern), FadeIn(kt)], 0.5),
        ])

        # ---- 8. copy one page --------------------------------------------------------------------------------------
        fd = frame(1, 1, "frame D", "1 map", GREEN_M)
        da = c_arrow(1, 1, GREEN_M)
        self.steps("The kernel copies just that page to a free frame, points the child at the copy, and makes it writable. "
                   "That takes about 2 microseconds.", [
            (lambda: [glow(fr[1][0], GOLD_M, 1.05)], 0.6),
            (lambda: [travel(Line(fr[1].get_center(), [FX, ROWS[1], 0]), YELLOW_M, 0.6)], 0.6),
            (lambda: [FadeIn(fd, scale=0.9), Transform(kt, T("kernel: copied 1 page", 20).move_to(kern))], 0.5),
            "points the child",
            (lambda: [ReplacementTransform(sa[1], da)], 0.7),
            "and makes it",
            (lambda: [Transform(ce[1][2], perm_t(TX, 1, "writable", GREEN_M)),
                      Transform(fr[1][2], cnt_t(-1, 1, "1 map", GREY_B))], 0.6),
            "That takes",
            (lambda: [FadeOut(fa), FadeOut(fl), travel(Line(da.get_start(), da.get_end()), GREEN_M, 0.5),
                      Transform(kt, T("one page copied in about 2 µs", 20).move_to(kern))], 0.7),
        ])

        # ---- 9. last sharer just gets write access back ----------------------------------------------------------
        cow = T("copy-on-write", 26, GREEN_M).move_to(rule)
        self.steps("Frame B now has one map, so the parent's next write there just gets write access back. "
                   "That's copy-on-write.", [
            (lambda: [glow(fr[1][0], GREEN_M, 1.05)], 0.7),
            "so the parent's",
            (lambda: [glow(pe[1][0], YELLOW_M, 1.04)], 0.5),
            "just gets",
            (lambda: [Transform(pe[1][2], perm_t(-TX, 1, "writable", GREEN_M)),
                      Transform(kt, T("no copy: frame B has 1 map", 20).move_to(kern))], 0.6),
            (lambda: [travel(Line(pa[1].get_start(), pa[1].get_end()), GREEN_M, 0.5)], 0.5),
            "That's copy-on-write",
            (lambda: [Transform(rule, cow)], 0.7),
        ])

        # ---- 10. honest bookkeeping fails --------------------------------------------------------------------------
        cap_ln = DashedLine([CAP_X, RAM_Y - 0.5, 0], [CAP_X, PR_Y + 0.45, 0], dash_length=0.1, stroke_width=2.5, color=GREY_B)
        cap_l = left_at(T("8 GB of RAM", 19, GREY_B), CAP_X + 0.2, RAM_Y)
        ram_bar = Rectangle(width=8 * U, height=BH, stroke_color=GREY_B, stroke_width=2.5).set_fill(BLACK, 1)
        ram_bar.move_to([X0 + 4 * U, RAM_Y, 0])
        lab_p = right_at(T("promised", 22, GREY_B), X0 - 0.2, PR_Y)
        lab_r = right_at(T("in RAM", 22, GREY_B), X0 - 0.2, RAM_Y)
        p_oth = seg(0, 1, PR_Y, GREY_B, "others", 16)
        p_jvm = seg(1, 5, PR_Y, BLUE_M, "JVM, 4 GB")
        r_oth = seg(0, 1, RAM_Y, GREY_B, "others", 16)
        r_jvm = seg(1, 5, RAM_Y, BLUE_M, "JVM, 4 GB")
        r_fc = seg(5, 6, RAM_Y, TEAL_M, "file cache", 15, 0.18)
        p_kid = seg(5, 9, PR_Y, GOLD_M, "its child, 4 GB")
        over = Rectangle(width=1 * U, height=BH, stroke_width=0).set_fill(RED_M, 0.45).move_to([CAP_X + U / 2, PR_Y, 0])
        nofork = T("total 9 GB: fork refused", 20, RED_M).move_to([X0 + 6 * U, PR_Y + 0.7, 0])
        phase1 = VGroup(pt, *pe, ct, *ce, *fr, fd, *pa, sa[0], sa[2], da, kern, kt, ram_t)
        self.steps("But fork promised the child memory the kernel never set aside. An honest kernel would refuse: "
                   "a 4 GB JVM on an 8 GB machine couldn't fork at all.", [
            (lambda: [FadeOut(phase1), FadeOut(rule)], 0.7),
            (lambda: [Transform(ram, ram_bar), FadeIn(lab_r)], 0.8),
            (lambda: [Create(cap_ln), FadeIn(cap_l), FadeIn(r_oth), FadeIn(r_jvm), FadeIn(r_fc)], 0.7),
            "An honest",
            (lambda: [FadeIn(lab_p), FadeIn(p_oth), FadeIn(p_jvm)], 0.6),
            "a 4 GB JVM",
            (lambda: [FadeIn(p_kid, shift=0.3 * RIGHT)], 0.7),
            (lambda: [FadeIn(over)], 0.4),
            "couldn't fork",
            (lambda: [FadeIn(nofork, shift=0.1 * UP)], 0.5),
        ])

        # ---- 11. overcommit -----------------------------------------------------------------------------------------
        pv = ValueTracker(9)
        ptot = always_redraw(lambda: left_at(T(f"promised in total: {int(round(pv.get_value()))} GB", 22, GOLD_M), -6.4, 2.75))
        p_big = Rectangle(width=4.0, height=BH, stroke_color=PURPLE_M, stroke_width=2).set_fill(PURPLE_M, 0.32)
        p_big.move_to([X0 + 9 * U + 2.0, PR_Y, 0])
        big_l = right_at(T("a batch job asks for 100 GB  →", 19, PURPLE_M), 6.5, PR_Y + 0.75)
        ok = T("returns at once", 20, GREEN_M).move_to([X0 + 2.5 * U, PR_Y + 0.75, 0])
        self.steps("So Linux overcommits. It says yes, and bets that most promises are never collected. "
                   "A request for 100 GB returns at once.", [
            (lambda: [FadeOut(over), FadeOut(nofork), FadeIn(ptot)], 0.6),
            "A request for",
            (lambda: [FadeIn(big_l), GrowFromEdge(p_big, LEFT), pv.animate.set_value(109)], 1.3),
            "returns at once",
            (lambda: [FadeIn(ok, shift=0.1 * UP)], 0.5),
        ])

        # ---- 12. the job touches its pages until RAM is full -------------------------------------------------------
        bv = ValueTracker(0.0)
        r_job = always_redraw(lambda: seg(8 - bv.get_value(), 8, RAM_Y, PURPLE_M, "batch job" if bv.get_value() > 1.2 else None))
        free_l = T("free", 17, GREY_C).move_to([X0 + 7 * U, RAM_Y, 0])
        self.steps("Then the batch job touches its pages. Each first touch takes a real frame, until RAM is full.", [
            (lambda: [FadeIn(free_l), VGroup(p_oth, p_jvm, p_kid, p_big, lab_p).animate.set_opacity(0.3), FadeOut(ok),
                      big_l.animate.set_opacity(0.4)], 0.6),
            (lambda: [FadeIn(r_job)], 0.1),
            (lambda: [bv.animate(rate_func=linear).set_value(1.0), FadeOut(free_l)], 0.9),
            "Each first touch",
            (lambda: [bv.animate(rate_func=linear).set_value(2.0)], 1.2),
            "until RAM is full",
            (lambda: [glow(ram, RED_M, 1.0)], 0.6),
        ])

        # ---- 13. a fault with nowhere to go; reclaim -----------------------------------------------------------------
        kern2 = RoundedRectangle(corner_radius=0.12, width=5.6, height=0.72, stroke_color=GOLD_M, stroke_width=2.5)
        kern2.set_fill(fillc(GOLD_M), 1).move_to([0, -2.6, 0])
        k2 = T("kernel: page fault, no free frame", 20).move_to(kern2)
        self.steps("The next touch faults, with no frame left and no error to return. "
                   "The kernel drops cached file pages, and the job fills those too.", [
            (lambda: [FadeIn(kern2), FadeIn(k2)], 0.6),
            "no error",
            (lambda: [glow(r_job[0], PURPLE_M, 1.0)], 0.7),
            "The kernel drops",
            (lambda: [Transform(k2, T("kernel: drop the file cache", 20).move_to(kern2)), FadeOut(r_fc)], 0.7),
            "and the job",
            (lambda: [bv.animate(rate_func=linear).set_value(3.0)], 0.9),
            (lambda: [Transform(k2, T("kernel: still no free frame", 20, RED_M).move_to(kern2))], 0.4),
        ])
        r_job.clear_updaters()

        # ---- 14. the OOM killer scores, and kills ----------------------------------------------------------------------
        sj = T("score: 4 GB", 18, BLUE_M).move_to([X0 + 3 * U, RAM_Y - 0.6, 0])
        sb = T("score: 3 GB", 18, PURPLE_M).move_to([X0 + 6.5 * U, RAM_Y - 0.6, 0])
        so = T("small", 18, GREY_B).move_to([X0 + 0.5 * U, RAM_Y - 0.6, 0])
        self.steps("So the out-of-memory killer scores each process by the memory it holds. The JVM is the biggest.", [
            (lambda: [Transform(k2, T("kernel: run the OOM killer", 20, RED_M).move_to(kern2))], 0.7),
            "scores each",
            (lambda: [FadeIn(so), FadeIn(sb), FadeIn(sj)], 0.7),
            "The JVM",
            (lambda: [glow(r_jvm[0], RED_M, 1.0), sj.animate.set_color(RED_M).scale(1.15)], 0.8),
        ])

        dead = seg(1, 5, RAM_Y, RED_M, "JVM: killed, exit code 137", 17, 0.12)
        self.steps("It gets SIGKILL, with no chance to clean up. The batch job asked for the last page, but the JVM died.", [
            (lambda: [Transform(k2, T("kernel: SIGKILL the JVM", 20, RED_M).move_to(kern2))], 0.5),
            (lambda: [Transform(r_jvm, dead)], 0.8),
            "The batch job",
            (lambda: [glow(r_job[0], PURPLE_M, 1.0)], 0.7),
            "but the JVM",
            (lambda: [glow(dead[0], RED_M, 1.0)], 0.7),
        ])

        # ---- 15. the sentence to keep ------------------------------------------------------------------------------------
        self.steps("fork copies only the pages that get written. The kernel promises more than it has, "
                   "and when the bill comes, the biggest process pays.", [
            (lambda: [FadeOut(so), FadeOut(sb), FadeOut(sj)], 0.5),
            "The kernel promises",
            (lambda: [Transform(p_oth, seg(0, 1, PR_Y, GREY_B, "others", 16)), Transform(p_jvm, seg(1, 5, PR_Y, BLUE_M, "JVM, 4 GB")),
                      Transform(p_kid, seg(5, 9, PR_Y, GOLD_M, "its child, 4 GB")),
                      p_big.animate.set_fill(PURPLE_M, 0.32).set_stroke(PURPLE_M, opacity=1),
                      lab_p.animate.set_opacity(1), big_l.animate.set_opacity(1)], 0.7),
            "the biggest",
            (lambda: [glow(dead[0], RED_M, 1.0)], 0.8),
        ])
        self.wait(0.6)
