from sfz import *

SAY.insert(0, (r"\bMySQL\b", "my S Q L"))
SAY.insert(0, (r"\bI/Os\b", "I Os"))
SAY.insert(0, (r"\b0\.95\b", "zero point nine five"))
SAY.insert(0, (r"\b7\.4\b", "seven point four"))
SAY.insert(0, (r"\b7\.7\b", "seven point seven"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
K, KW, KH = np.array([-4.75, 0.4, 0]), 2.9, 2.6          # the kitchen, later the database instance (compute)
SH, SH_W, SH_H = np.array([-4.75, -0.25, 0]), 2.3, 0.95  # its shelf, later its cache
WX0, WX1, WY0, WY1 = 0.0, 6.3, -1.3, 2.2                 # the warehouse, later the storage fleet
COL_W = (WX1 - WX0) / 3
ROWS = [0.95, -0.2]
CP_W, CP_H = 1.5, 0.75
LINK_Y = 0.4
STAT_Y, BAR_Y, CAP_Y = -1.85, -2.55, -3.2


def col_x(z):
    return WX0 + COL_W * (z + 0.5)


def copy_c(z, r):
    return np.array([col_x(z), ROWS[r], 0])


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

    def stamp(self, name):
        print(f"STAMP {name} {self.renderer.time:.1f}")


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(m, color=YELLOW_M, s=1.03):
    """Pulse an outline (Indicate would flood a filled box and hide its label)."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def swap(old, new, d=UP):
    """Replace one label with another: the old one leaves before the new one arrives, so they never overlap."""
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def chip_at(text, color, at, size=16):
    t = M(text, size, color)
    r = RoundedRectangle(corner_radius=0.06, width=t.width + 0.24, height=0.36, stroke_color=color, stroke_width=2).set_fill(BLACK, 1)
    return VGroup(r, t).move_to(at)


def travel_to(m, pts, rt):
    """Move a chip along a list of points, then fade it."""
    path = VMobject().set_points_as_corners([np.array(p) for p in pts])
    return Succession(MoveAlongPath(m, path, rate_func=smooth, run_time=rt), FadeOut(m, run_time=0.15))


class StorageCompute(Base):
    """found-05, section 2. A rented cloud computer's own disk vanishes with it. The café kitchen and its shelf; a
    warehouse down the road (a network disk) that survives, at the price of a trip per read or write; a database's
    log notes and 8 KB pages, mirrored to a second zone: 7.4 I/Os a transaction. Send only the slip: the log is the
    database (Aurora): 35 times the transactions at 0.95 I/Os each. Six copies in three zones, write 4, read 3: a
    zone fails, then a disk; nothing saved is lost; a 10-second repair. The price, the moral and a check."""

    # --- small state helpers: each returns animations and updates what is on screen ---
    def cap(self, s, color=GREY_B, size=24):
        new = (T(s, size, color) if isinstance(s, str) else s)
        fit(new, 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def put(self, key, mob):
        old = self.lab.get(key)
        self.lab[key] = mob
        return [swap(old, mob)]

    def drop(self, *keys):
        out = []
        for k in keys:
            m = self.lab.pop(k, None)
            if m is not None:
                out.append(FadeOut(m))
        return out

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def status(self, alive):
        w_ok, r_ok = alive >= 4, alive >= 3
        g = VGroup(T(f"copies left: {alive}", 22, WHITE),
                   VGroup(T("write needs 4", 22, GREY_B), tick(w_ok, 0.14)).arrange(RIGHT, buff=0.18),
                   VGroup(T("read needs 3", 22, GREY_B), tick(r_ok, 0.14)).arrange(RIGHT, buff=0.18)).arrange(RIGHT, buff=0.6)
        return self.put("status", fit(g, 6.3).move_to([(WX0 + WX1) / 2, STAT_Y, 0]))

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("Where the payments live", "storage apart from compute, and six copies in three zones")

        # ---------------- scene 1: the symptom ----------------
        kb = RoundedRectangle(corner_radius=0.16, width=KW, height=KH, stroke_color=BLUE_M, stroke_width=3).set_fill(fillc(BLUE_M), 1).move_to(K)
        k_t = T("rented computer", 24).move_to(K + [0, KH / 2 - 0.38, 0])
        sh = RoundedRectangle(corner_radius=0.1, width=SH_W, height=SH_H, stroke_color=GOLD_M, stroke_width=2.5).set_fill(fillc(GOLD_M), 1).move_to(SH)
        sh_t = T("its own disk", 20).move_to(SH + [0, 0.2, 0])
        sh_s = T("today's payments", 16, GREY_B).move_to(SH + [0, -0.2, 0])
        self.lab["k"], self.lab["sh"], self.lab["shs"] = k_t, sh_t, sh_s
        self.steps("A payments company rents a computer in the cloud to run its database. "
                   "That computer comes with its own disk, and the day's payments are written there.", [
            "rents a computer",
            (lambda: [FadeIn(kb), FadeIn(k_t)], 0.8),
            "its own disk",
            (lambda: [FadeIn(sh), FadeIn(sh_t), FadeIn(sh_s)], 0.7),
        ])
        boom = tick(False, 0.45).move_to(K + [0, 0.1, 0])
        self.steps("Then the computer fails, or the cloud moves it to another machine. Its disk goes with it.", [
            "fails",
            (lambda: [kb.animate.set_stroke(RED_M).set_fill(fillc(RED_M, 0.25), 1), Create(boom)], 0.7),
            "Its disk goes",
            (lambda: [VGroup(sh, sh_t, sh_s).animate.set_opacity(0.1)], 0.8),
        ])
        qm = T("?", 64, YELLOW_M).move_to([2.0, 0.4, 0])
        self.steps("So where should a database keep the payments it must never lose?", [
            (lambda: [FadeIn(qm, scale=0.6)], 0.6),
        ], after=0.5)

        # ---------------- scene 2: the kitchen and the warehouse ----------------
        boom2 = tick(False, 0.45).move_to(K + [0, 0.1, 0])
        self.steps("Picture the café kitchen. Its shelf holds the ingredients. If the kitchen burns down, the shelf goes with it. "
                   "That's the rented computer and its own disk.", [
            (lambda: [FadeOut(qm), FadeOut(boom), kb.animate.set_stroke(BLUE_M).set_fill(fillc(BLUE_M), 1),
                      sh.animate.set_opacity(1), *self.put("k", T("kitchen", 24).move_to(k_t)),
                      *self.put("sh", T("shelf", 20).move_to(sh_t)), *self.put("shs", T("ingredients", 16, GREY_B).move_to(sh_s))], 1.0),
            "burns down",
            (lambda: [Create(boom2), kb.animate.set_stroke(RED_M)], 0.6),
            "That's the rented",
            (lambda: [FadeOut(boom2), kb.animate.set_stroke(BLUE_M)], 0.6),
        ])
        wb = RoundedRectangle(corner_radius=0.16, width=WX1 - WX0, height=WY1 - WY0, stroke_color=TEAL_M, stroke_width=3) \
            .set_fill(fillc(TEAL_M, 0.08), 1).move_to([(WX0 + WX1) / 2, (WY0 + WY1) / 2, 0])
        w_t = T("warehouse", 24).move_to([(WX0 + WX1) / 2, WY1 + 0.35, 0])
        link = Arrow([K[0] + KW / 2 + 0.08, LINK_Y, 0], [WX0 - 0.08, LINK_Y, 0], buff=0, stroke_width=3, color=GREY_B,
                     max_tip_length_to_length_ratio=0.08)
        link_t = T("down the road", 18, GREY_B).move_to([(K[0] + KW / 2 + WX0) / 2, LINK_Y - 0.3, 0])
        cps = {}

        def copy_box(z, r, color=TEAL_M):
            b = RoundedRectangle(corner_radius=0.08, width=CP_W, height=CP_H, stroke_color=color, stroke_width=2.5).set_fill(fillc(color), 1)
            return VGroup(b, M(f"{'abc'[z]}{r + 1}", 20).move_to(b)).move_to(copy_c(z, r))

        cps[(0, 0)] = copy_box(0, 0)
        self.lab.update(w=w_t, link=link_t)
        self.steps("So keep the stock in a warehouse down the road. A fire in the kitchen loses nothing. "
                   "In the cloud, that's a network disk. It lives on the provider's storage machines, and it survives.", [
            "a warehouse",
            (lambda: [FadeIn(wb), FadeIn(w_t), GrowArrow(link), FadeIn(link_t), FadeIn(cps[(0, 0)], scale=0.8)], 1.0),
            "A fire",
            (lambda: [glow(cps[(0, 0)][0], TEAL_M, 1.08)], 0.8),
            "a network disk",
            (lambda: [*self.put("w", T("network disk", 24).move_to(w_t)), *self.put("link", T("the network", 18, GREY_B).move_to(link_t))], 0.7),
        ])
        self.steps("The catch: every fetch is now a trip down the road. Every read or write is a call over the network.", [
            (lambda: [travel_to(chip_at("read", WHITE, link.get_start()), [link.get_start(), link.get_end(), copy_c(0, 0)], 1.0)], 1.2),
            (lambda: [travel_to(chip_at("write", WHITE, link.get_start()), [link.get_start(), link.get_end(), copy_c(0, 0)], 1.0)], 1.2),
        ])

        # ---------------- scene 3: a database makes a lot of trips ----------------
        cps[(1, 0)] = copy_box(1, 0)
        zl = VGroup(*[T(f"zone {'abc'[z]}", 18, GREY_B).move_to([col_x(z), WY1 - 0.3, 0]) for z in range(3)])
        seps = VGroup(*[DashedLine([WX0 + COL_W * z, WY1 - 0.1, 0], [WX0 + COL_W * z, WY0 + 0.1, 0], dash_length=0.08,
                                   stroke_width=1.5, color=GREY_D) for z in (1, 2)])

        def trip(text, color, target, rt=0.9):
            c = chip_at(text, color, link.get_start())
            return travel_to(c, [link.get_start(), link.get_end(), copy_c(*target)], rt)

        self.steps("And a database makes a lot of trips. It saves each change twice. First a short note at the end of its log, "
                   "a file it only adds to, so a crash loses nothing. Later, the changed pages, the blocks its tables live in, often 8 kilobytes each.", [
            "a short note",
            (lambda: [trip("note", BLUE_M, (0, 0))], 1.1),
            "Later, the changed",
            (lambda: [trip("page 8 KB", GOLD_M, (0, 0), 1.2)], 1.3),
            (lambda: [trip("page 8 KB", GOLD_M, (0, 0), 1.2)], 1.3),
        ])
        self.steps("Now keep a mirror in a second availability zone, a separate building with its own power and network. Every trip happens twice.", [
            "a mirror",
            (lambda: [FadeIn(zl), Create(seps), FadeIn(cps[(1, 0)], scale=0.8)], 0.9),
            "Every trip",
            (lambda: [LaggedStart(trip("note", BLUE_M, (0, 0)), trip("note", BLUE_M, (1, 0)), trip("page 8 KB", GOLD_M, (0, 0)),
                                  trip("page 8 KB", GOLD_M, (1, 0)), lag_ratio=0.3)], 2.0),
        ])
        io = VGroup(T("I/Os per", 20, GREY_B), T("transaction: 7.4", 20, RED_M)).arrange(DOWN, buff=0.1).move_to([(K[0] + KW / 2 + WX0) / 2, 1.35, 0])
        self.steps("Amazon counted. A mirrored MySQL database, a popular free one, needed 7.4 reads or writes to storage for each transaction. "
                   "Each of those is called an I/O.", [
            "needed 7.4",
            (lambda: [*self.put("io", io), *self.cap("mirrored MySQL: 7.4 trips to storage per transaction", RED_M)], 0.7),
            "called an I/O",
            (lambda: self.cap("I/O: one read or write to storage", WHITE), 0.6),
        ])
        self.steps("Wouldn't it be nice to send just the short note?", [
            (lambda: self.cap("send just the short note?", YELLOW_M), 0.6),
        ], after=0.5)

        # ---------------- scene 4: send only the slip ----------------
        self.steps("Back to the kitchen. The cook sends the warehouse only a slip: used two eggs. "
                   "The warehouse clerks update their own stock pages from the slips. The kitchen keeps only today's ingredients on its shelf.", [
            (lambda: [*self.uncap(), *self.put("w", T("warehouse", 24).move_to(w_t)), *self.put("link", T("down the road", 18, GREY_B).move_to(link_t))], 0.6),
            "only a slip",
            (lambda: [LaggedStart(trip("slip", BLUE_M, (0, 0)), trip("slip", BLUE_M, (1, 0)), lag_ratio=0.2)], 1.2),
            "update their own",
            (lambda: [glow(cps[(0, 0)][0], TEAL_M, 1.08), glow(cps[(1, 0)][0], TEAL_M, 1.08)], 0.9),
            "keeps only",
            (lambda: [*self.put("shs", T("today's ingredients", 16, GREY_B).move_to(sh_s)), glow(sh, GOLD_M, 1.05)], 0.8),
        ])
        self.steps("Now map it. The kitchen is the database instance, the computer doing the work, called compute. "
                   "The warehouse is a fleet of storage machines.", [
            "The kitchen is",
            (lambda: [*self.put("k", T("database: compute", 20).move_to(k_t)), glow(kb, BLUE_M, 1.02)], 0.7),
            "The warehouse is",
            (lambda: [*self.put("w", T("storage machines", 24).move_to(w_t)), *self.put("link", T("the network", 18, GREY_B).move_to(link_t))], 0.7),
        ])
        pages = [chip_at("page", GOLD_M, copy_c(z, 0) + [0, -0.62, 0]) for z in (0, 1)]
        self.steps("The slip is a redo log record, a short note saying what a change did. "
                   "The storage machines build the 8 kilobyte pages themselves, so pages never cross the network on a write.", [
            (lambda: [trip("redo record", BLUE_M, (0, 0), 1.1)], 1.2),
            "build the 8",
            (lambda: [*self.cap("the storage machines build the 8 KB pages from the notes", WHITE),
                      *[FadeIn(pg, shift=0.1 * UP) for pg in pages]], 0.8),
        ])
        self.steps("And the shelf is only a cache, a quick copy that can be refilled.", [
            (lambda: [*self.put("sh", T("cache", 20).move_to(sh_t)), *self.put("shs", T("a quick copy", 16, GREY_B).move_to(sh_s)),
                      *[FadeOut(pg) for pg in pages]], 0.7),
        ])
        self.steps("This is called separating storage from compute. Amazon's Aurora, a cloud database built from MySQL, "
                   "sums it up in one line: the log is the database.", [
            (lambda: self.cap("separating storage from compute", WHITE), 0.6),
            "the log is the",
            (lambda: self.cap("Aurora: the log is the database", YELLOW_M, 28), 0.7),
        ])

        # ---------------- scene 5: the numbers ----------------
        self.steps("Same 30-minute test, same size of machine. Mirrored MySQL: 780,000 transactions, at 7.4 I/Os each. "
                   "Aurora: 27 million, at 0.95 I/Os each.", [
            (lambda: self.cap("30 minutes of writes, same machine size", WHITE), 0.6),
            "Mirrored MySQL",
            (lambda: self.cap("mirrored MySQL: 780,000 transactions, 7.4 I/Os each", RED_M), 0.6),
            "Aurora: 27",
            (lambda: [*self.cap("Aurora: 27,378,000 transactions, 0.95 I/Os each", GREEN_M),
                      *self.put("io", VGroup(T("I/Os per", 20, GREY_B), T("transaction: 0.95", 20, GREEN_M)).arrange(DOWN, buff=0.1).move_to(io))], 0.7),
        ])
        self.steps("That's 35 times the transactions, with 7.7 times fewer I/Os each. And Aurora was keeping six copies of the data. "
                   "More breakfasts, fewer trips.", [
            (lambda: self.cap("35 times the transactions,  7.7 times fewer I/Os each", GREEN_M), 0.6),
            "six copies",
            (lambda: [*[FadeIn(cps.setdefault(k, copy_box(*k)), scale=0.8) for k in [(0, 1), (1, 1), (2, 0), (2, 1)]],
                      *self.cap("while keeping six copies", WHITE)], 0.9),
        ])

        # ---------------- scene 6: six copies, three zones, quorums ----------------
        self.steps("Six copies, kept how? Aurora cuts the data into 10-gigabyte segments. Each segment has six copies, two in each of three zones.", [
            (lambda: [*self.uncap(), *self.drop("io")], 0.4),
            "10-gigabyte",
            (lambda: self.cap("one 10 GB segment: six copies, two in each of three zones", WHITE), 0.6),
            "two in each",
            (lambda: [LaggedStart(*[glow(cps[(z, r)][0], TEAL_M, 1.08) for z in range(3) for r in range(2)], lag_ratio=0.15)], 1.2),
        ])

        def acks(n):
            ks = [(z, r) for z in range(3) for r in range(2)]
            return [LaggedStart(*[trip("redo", BLUE_M, k, 0.8) for k in ks], lag_ratio=0.08)]

        self.steps("A write counts once four copies have it. A read needs three. "
                   "Those numbers are quorums: how many copies must answer before an operation counts.", [
            (lambda: acks(6), 1.4),
            "A write counts",
            (lambda: self.status(6), 0.6),
            "Those numbers",
            (lambda: self.cap("quorum: how many copies must answer before an operation counts", YELLOW_M), 0.6),
        ])

        # ---------------- scene 7: a zone fails, then a disk ----------------
        xs = {}

        def kill(k):
            xs[k] = tick(False, 0.2).move_to(copy_c(*k))
            return [cps[k][0].animate.set_stroke(RED_M).set_fill(fillc(RED_M, 0.25), 1), cps[k][1].animate.set_opacity(0.3), Create(xs[k])]

        self.steps("Now a whole zone fails. Its power, its network, or a bad change that hits every machine in it. "
                   "Two copies gone. Can we still write? Pause and guess.", [
            (lambda: self.uncap(), 0.3),
            "a whole zone",
            (lambda: [*kill((0, 0)), *kill((0, 1))], 0.8),
            "Two copies gone",
            (lambda: [*self.put("status", VGroup(T("copies left: 4", 22, WHITE), T("write?", 22, YELLOW_M), T("read?", 22, YELLOW_M))
                                .arrange(RIGHT, buff=0.6).move_to([(WX0 + WX1) / 2, STAT_Y, 0]))], 0.6),
            "Pause and guess",
            (lambda: self.cap("pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        alive = [(1, 0), (1, 1), (2, 0), (2, 1)]
        self.steps("Yes. Four copies are left, and a write needs four.", [
            (lambda: [*self.uncap(), *self.status(4), LaggedStart(*[trip("redo", BLUE_M, k, 0.8) for k in alive], lag_ratio=0.1)], 1.2),
        ])
        self.steps("Then, while that zone is down, a disk in zone c dies. Three left. Writes stop. Reads still work.", [
            "a disk in zone c",
            (lambda: kill((2, 1)), 0.7),
            "Three left",
            (lambda: self.status(3), 0.6),
        ])
        self.stamp("three-left")
        self.steps("Did we lose a saved write? No. Every saved write reached four copies. "
                   "Any three copies include at least one of those four, because three plus four is more than six.", [
            "Every saved write",
            (lambda: self.cap("every saved write: on 4 copies.   any 3 copies overlap them: 3 + 4 > 6", WHITE), 0.7),
            "Any three",
            (lambda: [LaggedStart(*[glow(cps[k][0], GREEN_M, 1.08) for k in [(1, 0), (1, 1), (2, 0)]], lag_ratio=0.2)], 1.0),
        ])
        newc = copy_box(0, 0, GREEN_M)

        def copy_dot():
            d = Dot(radius=0.07, color=GREEN_M).move_to(copy_c(1, 0))
            return Succession(FadeIn(d, run_time=0.05), MoveAlongPath(d, Line(copy_c(1, 0), copy_c(0, 0)), run_time=0.5), FadeOut(d, run_time=0.1))
        self.steps("Meanwhile, the storage fleet copies the segment onto a new machine. Ten gigabytes take about 10 seconds. "
                   "That's why the segments are small. Aurora can't stop disks failing, but it can repair them fast.", [
            (lambda: [FadeOut(xs[(0, 0)]), FadeOut(cps[(0, 0)])], 0.4),
            "copies the segment",
            (lambda: [FadeIn(newc, scale=0.8),
                      LaggedStart(*[copy_dot() for _ in range(4)], lag_ratio=0.25)], 1.6),
            "Ten gigabytes",
            (lambda: [*self.status(4), *self.cap("10 GB over a 10 Gbit/s link: about 10 seconds", GREEN_M)], 0.7),
            "Aurora can't",
            (lambda: self.cap("you can't stop disks failing; you can repair them fast", WHITE), 0.6),
        ])

        # ---------------- scene 8: the price ----------------
        self.steps("The price is a network trip on every write. Newer designs go further. They keep the durable copy in object storage, "
                   "cheap file storage like Amazon S3, to save on fees for bytes that cross between zones. They pay with slower writes.", [
            (lambda: [self.cap("the price: a network trip on every write", WHITE)[0], glow(link, RED_M, 1.0)], 0.7),
            "object storage",
            (lambda: self.cap("newer designs: the durable copy in object storage, like Amazon S3", WHITE), 0.6),
            "They pay",
            (lambda: self.cap("cheaper across zones, slower writes", GOLD_M), 0.6),
        ])

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So where should the payments live? Not on a computer that can vanish. In the warehouse: six copies, in three buildings. "
                   "The kitchen's shelf is only a cache.", [
            (lambda: self.cap("where should the payments live?", WHITE), 0.5),
            "In the warehouse",
            (lambda: [glow(wb, TEAL_M, 1.01)], 0.9),
            "The kitchen's shelf",
            (lambda: [glow(sh, GOLD_M, 1.05)], 0.8),
        ])
        self.steps("Where is the durable copy, and what is only a cache? Ask that first, of any system.", [
            (lambda: self.cap("where is the durable copy, and what is only a cache?", YELLOW_M, 28), 0.7),
        ], after=0.6)
        boom3 = tick(False, 0.45).move_to(K + [0, 0.1, 0])
        self.steps("One quick check. The database instance crashes: the kitchen burns down. What's lost? Pause and think.", [
            "crashes",
            (lambda: [kb.animate.set_stroke(RED_M).set_fill(fillc(RED_M, 0.25), 1), Create(boom3), *self.cap("the instance crashes: what's lost?", WHITE)], 0.7),
            "Pause and think",
            (lambda: self.cap("pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("Only the shelf, a cache. Every saved change is in the warehouse. A new instance starts, and refills its shelf.", [
            (lambda: [*self.cap("only the cache. every saved change is in storage.", GREEN_M, 28), VGroup(sh, self.lab["sh"], self.lab["shs"]).animate.set_opacity(0.15)], 0.7),
            "A new instance",
            (lambda: [FadeOut(boom3), kb.animate.set_stroke(BLUE_M).set_fill(fillc(BLUE_M), 1)], 0.6),
            "refills its shelf",
            (lambda: [travel_to(chip_at("page", GOLD_M, copy_c(1, 0)), [copy_c(1, 0), link.get_end(), link.get_start()], 1.0)], 1.2),
            (lambda: [VGroup(sh, self.lab["sh"], self.lab["shs"]).animate.set_opacity(1)], 0.5),
        ], after=0.3)
        self.play(*self.cap("where is the durable copy, and what is only a cache?", YELLOW_M, 28), run_time=0.7)
        self.wait(2.0)
