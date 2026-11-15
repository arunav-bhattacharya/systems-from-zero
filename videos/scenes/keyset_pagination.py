from sfz import *

SAY.insert(0, (r"\bOFFSET\b", "offset"))
SAY.insert(0, (r"\bLIMIT\b", "limit"))

QF = 15
X_L = -6.5
Q_Y = [3.3, 2.95, 2.6]
SX0, SX1, SY, SH = -6.2, 6.2, 0.75, 0.36       # the index's leaf level, newest entry on the left
ROOT = np.array([0, 2.0, 0])
INNER_Y = 1.42
INNER_X = [-4.65, -1.55, 1.55, 4.65]
N = 1_000_000
ZY, ZX0, ZP = -0.55, -5.3, 0.74                 # zoomed-in list of the newest entries
ST_HDR, ST_Y = -1.45, [-1.85, -2.25, -2.65, -3.05]
X_RR, X_TM = 1.9, 4.1                           # stats: rows read and time, right edges


def sx(k):
    """x on the leaf level of the k-th entry from the newest."""
    return SX0 + (SX1 - SX0) * k / N


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


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def qline(s, k, hl=None):
    return left_at(M(s, QF, t2c=hl or {}), X_L, Q_Y[k])


def swap(old, new):
    return [FadeOut(old), FadeIn(new)]


def node(x, y, w=1.1, h=0.42, color=GREY_B):
    """An index page: a box with three key slots."""
    r = RoundedRectangle(corner_radius=0.07, width=w, height=h, stroke_color=color, stroke_width=2).set_fill(fillc(GREY_B, 0.1), 1)
    r.move_to([x, y, 0])
    for f in (-1 / 6, 1 / 6):
        r.add(Line([x + f * w, y - h / 2 + 0.07, 0], [x + f * w, y + h / 2 - 0.07, 0], stroke_width=1.2, color=GREY_D))
    return r


def zx(k):
    return ZX0 + k * ZP


def zchip(pid, k, color=WHITE):
    r = RoundedRectangle(corner_radius=0.06, width=0.62, height=0.46, stroke_color=color, stroke_width=2)
    r.set_fill(fillc(color, 0.16), 1).move_to([zx(k), ZY, 0])
    return VGroup(r, M(str(pid), 17, WHITE).move_to([zx(k), ZY, 0]))


def stat(label, rows, tm, k, color=WHITE):
    y = ST_Y[k]
    return VGroup(left_at(M(label, 15, color), X_L, y), right_at(M(rows, 16, color), X_RR, y), right_at(M(tm, 16, color), X_TM, y))


class KeysetPagination(Base):
    """sql-08, section 3 (with section 4's keyset pagination): payments newest first, 20 a page, through an index on
    (created_at, payment_id). LIMIT 20 OFFSET 100000 walks 100,020 entries to return 20 (2,865 buffers, about 48 ms), and
    page 45,001 reads 900,020 rows (1.2 s). A new payment shifts OFFSET pages, so page 2 repeats payment 33. Keyset
    pagination: WHERE (created_at, payment_id) < the last row's key descends the index once and reads 20 entries,
    5 buffers, on any page; new rows sort before the cursor and shift nothing."""

    def construct(self):
        self.title_card("Keyset pagination", "jump to the next page instead of counting to it")

        # ---- the index -----------------------------------------------------------------------------------------------
        leaf = Rectangle(width=SX1 - SX0, height=SH, stroke_color=GREY_B, stroke_width=2).set_fill(fillc(GREY_B, 0.12), 1)
        leaf.move_to([(SX0 + SX1) / 2, SY, 0])
        ticks = VGroup(*[Line([sx(i * N / 64), SY - SH / 2, 0], [sx(i * N / 64), SY + SH / 2, 0], stroke_width=1, color=GREY_D)
                         for i in range(1, 64)])
        root = node(*ROOT[:2])
        inner = [node(x, INNER_Y) for x in INNER_X]
        edges = VGroup(*[Line(root.get_bottom(), n.get_top(), stroke_width=1.5, color=GREY_D) for n in inner],
                       *[Line(n.get_bottom(), [sx((k + 0.5) * N / 4), SY + SH / 2, 0], stroke_width=1.5, color=GREY_D)
                         for k, n in enumerate(inner)])
        ilab = left_at(T("index on (created_at, payment_id): 1,000,000 payments", 20, GREY_B), SX0, SY - 0.45)
        newest = left_at(T("newest", 18, GREEN_M), SX0, SY + 0.42)
        oldest = right_at(T("oldest", 18, GREY_B), SX1, SY + 0.42)
        self.steps("The admin console lists payments newest first, 20 to a page. "
                   "An index on created at and payment id keeps every payment in exactly that order.", [
            (lambda: [FadeIn(leaf), FadeIn(ticks), FadeIn(newest), FadeIn(oldest)], 0.9),
            "An index",
            (lambda: [FadeIn(root), *[FadeIn(n) for n in inner], Create(edges)], 1.0),
            (lambda: [FadeIn(ilab, shift=0.1 * UP)], 0.6),
        ])

        q1 = qline("SELECT payment_id, created_at, amount_minor FROM payments", 0)
        q2 = qline("ORDER BY created_at DESC, payment_id DESC LIMIT 20 OFFSET 0", 1, {"LIMIT 20 OFFSET 0": YELLOW_M})
        tk = ValueTracker(0)
        green = Rectangle(width=0.06, height=SH + 0.08, stroke_width=0).set_fill(GREEN_M, 1).move_to([SX0 + 0.03, SY, 0])

        def red_region():
            k = tk.get_value()
            w = max(0.001, sx(k) - SX0)
            return Rectangle(width=w, height=SH, stroke_width=0).set_fill(RED_M, 0.55).move_to([SX0 + w / 2, SY, 0])

        red = always_redraw(red_region)
        st_hdr = VGroup(left_at(M("query", 15, GREY_B), X_L, ST_HDR), right_at(M("rows read", 15, GREY_B), X_RR, ST_HDR),
                        right_at(M("time", 15, GREY_B), X_TM, ST_HDR))
        st_rule = Line([X_L, ST_HDR - 0.22, 0], [X_TM, ST_HDR - 0.22, 0], stroke_width=1.5, color=GREY_D)
        S = [stat("page 1, OFFSET 0", "20", "0.15 ms", 0, GREEN_M)]
        self.steps("Each page asks for LIMIT 20 and an OFFSET. "
                   "Page 1 reads the newest 20 entries and stops, in a fraction of a millisecond.", [
            (lambda: [FadeIn(q1, shift=0.1 * DOWN), FadeIn(q2, shift=0.1 * DOWN)], 0.8),
            "Page 1 reads",
            (lambda: [FadeIn(green, scale=1.5), FadeIn(st_hdr), Create(st_rule)], 0.7),
            "in a fraction",
            (lambda: [FadeIn(S[0], shift=0.1 * UP)], 0.7),
        ])

        q2b = qline("ORDER BY created_at DESC, payment_id DESC LIMIT 20 OFFSET 100000", 1, {"LIMIT 20 OFFSET 100000": YELLOW_M})
        def counter():
            k = tk.get_value()
            g = VGroup(M(f"{int(k + 20):,}", 18, RED_M), T("entries read", 20, RED_M)).arrange(RIGHT, buff=0.15)
            if sx(k) > 2:
                return right_at(g, sx(k) - 0.15, SY - 0.5)
            return left_at(g, max(sx(k) + 0.15, SX0 + 0.2), SY - 0.5)

        cnt = always_redraw(counter)

        self.steps("Page 5,001 is OFFSET 100,000. An index stores no row numbers, so PostgreSQL can't jump to entry 100,001. "
                   "It starts at the newest and walks.", [
            (lambda: swap(q2, q2b), 0.7),
            "An index stores",
            (lambda: [Indicate(root, color=GREY_A), *[Indicate(n, color=GREY_A) for n in inner]], 0.9),
            "It starts",
            (lambda: [FadeOut(ilab), glow(green, GREEN_M, 1.5)], 0.7),
        ])

        S.append(stat("page 5,001, OFFSET 100,000", "100,020", "48 ms", 1, RED_M))
        self.steps("It reads 100,020 rows, and throws away 100,000 of them to return 20. "
                   "That takes about 50 milliseconds.", [
            (lambda: [FadeIn(red), FadeIn(cnt)], 0.3),
            (lambda: [tk.animate(rate_func=linear).set_value(100_000), green.animate.move_to([sx(100_000) + 0.03, SY, 0])], 3.2),
            "That takes",
            (lambda: [FadeIn(S[1], shift=0.1 * UP)], 0.7),
        ])

        q2c = qline("ORDER BY created_at DESC, payment_id DESC LIMIT 20 OFFSET 900000", 1, {"LIMIT 20 OFFSET 900000": YELLOW_M})
        S.append(stat("page 45,001, OFFSET 900,000", "900,020", "1.2 s", 2, RED_M))
        self.steps("Page 45,001 reads 900,020 rows and takes 1.2 seconds. Every page costs more than the one before.", [
            (lambda: swap(q2b, q2c), 0.6),
            (lambda: [tk.animate(rate_func=linear).set_value(900_000), green.animate.move_to([sx(900_000) + 0.03, SY, 0])], 2.6),
            (lambda: [FadeIn(S[2], shift=0.1 * UP)], 0.6),
        ])

        # ---- OFFSET shifts when rows arrive ---------------------------------------------------------------------------
        Z = {p: zchip(p, k + 1) for k, p in enumerate(range(37, 27, -1))}
        zl = DashedLine([SX0, SY - SH / 2, 0], [zx(1) - 0.36, ZY + 0.26, 0], dash_length=0.06, stroke_width=1.5, color=GREY_C)
        zr = DashedLine([SX0 + 0.06, SY - SH / 2, 0], [zx(10) + 0.36, ZY + 0.26, 0], dash_length=0.06, stroke_width=1.5,
                        color=GREY_C)
        ztitle = right_at(T("zoomed in: the newest entries", 20, GREY_B), SX1, ZY + 0.62)

        def pbox(k0, color, label):
            r = RoundedRectangle(corner_radius=0.08, width=5 * ZP + 0.06, height=0.66, stroke_color=color, stroke_width=2.5)
            r.move_to([(zx(k0) + zx(k0 + 4)) / 2, ZY, 0])
            return VGroup(r, T(label, 18, color).next_to(r, DOWN, buff=0.08))

        p1 = pbox(1, GREEN_M, "page 1")
        q2d = qline("ORDER BY created_at DESC, payment_id DESC LIMIT 5 OFFSET 0", 1, {"LIMIT 5 OFFSET 0": YELLOW_M})
        self.steps("OFFSET also goes wrong while payments arrive. "
                   "With five to a page, page 1 shows payments 37 to 33.", [
            (lambda: [FadeOut(red), FadeOut(cnt), green.animate.move_to([SX0 + 0.03, SY, 0]), *swap(q2c, q2d),
                      *[s.animate.set_opacity(0.35) for s in S], st_hdr.animate.set_opacity(0.35)], 0.8),
            "With five",
            (lambda: [Create(zl), Create(zr), LaggedStart(*[FadeIn(Z[p], shift=0.1 * DOWN) for p in Z], lag_ratio=0.08),
                      FadeIn(ztitle)], 1.2),
            "page 1 shows",
            (lambda: [Create(p1[0]), FadeIn(p1[1])], 0.7),
        ])

        new38 = zchip(38, 0, GOLD_M)
        p2 = pbox(6, RED_M, "page 2, OFFSET 5")
        q2e = qline("ORDER BY created_at DESC, payment_id DESC LIMIT 5 OFFSET 5", 1, {"LIMIT 5 OFFSET 5": YELLOW_M})
        dup = Z[33]
        self.steps("Then a new payment comes in at the front. Every row slides back one place, "
                   "so page 2, OFFSET 5, starts with payment 33 again.", [
            (lambda: [FadeOut(p1), FadeIn(new38, shift=0.4 * DOWN)], 0.7),
            "Every row slides",
            (lambda: [new38.animate.move_to([zx(1), ZY, 0]), *[Z[p].animate.shift(ZP * RIGHT) for p in Z]], 0.9),
            "so page 2",
            (lambda: [*swap(q2d, q2e), Create(p2[0]), FadeIn(p2[1])], 0.7),
            "starts with payment 33",
            (lambda: [dup[0].animate.set_stroke(RED_M, 3).set_fill(fillc(RED_M, 0.3), 1)], 0.6),
            (lambda: [Wiggle(dup)], 0.7),
        ])

        # ---- keyset ---------------------------------------------------------------------------------------------------
        undo = [Z[p].animate.shift(ZP * LEFT) for p in Z if p != 33] + [Transform(Z[33], zchip(33, 5))]
        cur = Triangle(color=YELLOW_M, fill_opacity=1, stroke_width=0).scale(0.11).rotate(PI)
        cur.move_to([zx(5) + ZP / 2, ZY + 0.42, 0])
        curl = T("cursor: the last row shown", 18, YELLOW_M).next_to(cur, UP, buff=0.08)
        self.steps("Fix both by not counting. The client already knows where the last page ended: the last row it showed.", [
            (lambda: [FadeOut(p2), FadeOut(new38), *undo], 0.8),
            "The client",
            (lambda: [Create(p1[0]), FadeIn(p1[1])], 0.6),
            "the last row",
            (lambda: [FadeIn(cur, shift=0.15 * DOWN), FadeIn(curl), glow(Z[33][0], YELLOW_M, 1.1)], 0.8),
        ])

        k1 = qline("SELECT payment_id, created_at, amount_minor FROM payments", 0)
        k2 = qline("WHERE (created_at, payment_id) < (:last_at, :last_id)", 1,
                   {"WHERE (created_at, payment_id) < (:last_at, :last_id)": YELLOW_M})
        k3 = qline("ORDER BY created_at DESC, payment_id DESC LIMIT 20", 2)
        self.steps("Keyset pagination asks only for rows that sort after that key, "
                   "comparing created at and payment id as a pair.", [
            (lambda: [*swap(q1, k1), *swap(q2e, k2), FadeIn(k3)], 0.9),
            "comparing",
            (lambda: [Indicate(k2, color=YELLOW_M, scale_factor=1.0)], 1.0),
        ])

        # descend the index to the cursor of page 5,001
        ckey = chip("cursor: (2026-09-28 00:21:42, 900050)", YELLOW_M, 16, mono=True)
        left_at(ckey, sx(100_000) - 0.2, SY - 0.62)
        path = VMobject().set_points_as_corners([ROOT, inner[0].get_center(), [sx(100_000), SY, 0]])
        dot = Dot(radius=0.09, color=YELLOW_M).move_to(ROOT)
        S.append(stat("page 5,001, keyset", "20", "0.7 ms", 3, GREEN_M))
        self.steps("On page 5,001, PostgreSQL descends the index once, straight to the cursor, and reads the next 20. "
                   "Under a millisecond, like page 1.", [
            (lambda: [FadeOut(VGroup(p1, cur, curl, zl, zr, ztitle, *Z.values())),
                      *[s.animate.set_opacity(1) for s in S], st_hdr.animate.set_opacity(1)], 0.8),
            (lambda: [FadeIn(dot, scale=0.5), root.animate.set_stroke(YELLOW_M, 3)], 0.4),
            (lambda: [MoveAlongPath(dot, path, rate_func=smooth), inner[0].animate.set_stroke(YELLOW_M, 3)], 1.3),
            "and reads",
            (lambda: [green.animate.move_to([sx(100_000) + 0.03, SY, 0]), FadeOut(dot), FadeIn(ckey, shift=0.1 * UP)], 0.6),
            "Under a millisecond",
            (lambda: [FadeIn(S[3], shift=0.1 * UP)], 0.7),
        ])

        self.steps("Payments that arrive later sort before the cursor. They land on page 1 and shift nothing.", [
            (lambda: [glow(newest, GREEN_M, 1.2), root.animate.set_stroke(GREY_B, 2), inner[0].animate.set_stroke(GREY_B, 2)], 0.9),
            "They land",
            (lambda: [Flash([SX0 + 0.05, SY, 0], color=GOLD_M, flash_radius=0.35)], 0.8),
            "shift nothing",
            (lambda: [glow(green, GREEN_M, 1.5)], 0.8),
        ])

        give = chip("the price: next and previous only, no jump to page 4,000", GREY_B, 20).move_to([2.6, -0.8, 0])
        self.steps("You give up page numbers: there's no jump to page 4,000. "
                   "For an infinite scroll or an export job, that costs nothing.", [
            (lambda: [*[s.animate.set_opacity(0.35) for s in S[:3]]], 0.6),
            "no jump",
            (lambda: [FadeIn(give, shift=0.1 * UP)], 0.6),
            (lambda: [Indicate(S[3], color=GREEN_M, scale_factor=1.0)], 0.9),
        ])

        self.steps("OFFSET counts its way to the page, and reads every row it skips. "
                   "A cursor remembers where you stopped, and the index jumps straight there.", [
            (lambda: [FadeOut(give), *[s.animate.set_opacity(1) for s in S[1:3]], Indicate(S[2], color=RED_M, scale_factor=1.0)], 1.0),
            "A cursor",
            (lambda: [Indicate(S[3], color=GREEN_M, scale_factor=1.0), glow(green, GREEN_M, 1.5)], 1.0),
        ])
        self.wait(0.6)
