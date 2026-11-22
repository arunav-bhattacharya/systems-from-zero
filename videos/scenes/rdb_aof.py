from sfz import *

SAY.insert(0, (r"\bBGSAVE\b", "B G save"))
SAY.insert(0, (r"\bSAVE\b", "save"))
SAY.insert(0, (r"\bdump\.rdb\b", "dump dot R D B"))
SAY.insert(0, (r"\bkill -9\b", "kill minus nine"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
PA = (-6.5, -2.9, 3.1, 1.3)                  # the parent process (x0, x1, top, bot)
CH = (2.9, 6.5, 3.1, 1.3)                    # the child process
PG_Y, PG_W, PG_H = -0.35, 2.6, 1.4            # memory pages A, B, C
PG_X = {"A": -3.1, "B": 0.0, "C": 3.1}
BP = np.array([-3.1, -2.2, 0])                # where B' appears
DK = (2.4, 6.5, -1.55, -2.75)                    # the disk
BAR_Y, CAP_Y = -2.72, -3.27


def cx(b):
    return (b[0] + b[1]) / 2


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
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def frame(x0, x1, top, bot, color, r=0.14):
    return RoundedRectangle(corner_radius=r, width=x1 - x0, height=top - bot, stroke_color=color,
                            stroke_width=3).set_fill(fillc(color), 1).move_to([(x0 + x1) / 2, (top + bot) / 2, 0])


def harrow(x0, x1, y, color=GREY_B):
    return Arrow([x0, y, 0], [x1, y, 0], buff=0, stroke_width=3, color=color, max_tip_length_to_length_ratio=0.15)


def run_pts(pts, color=YELLOW_M, rt=0.7, r=0.07):
    """A message dot running along a polyline, visible only while it runs."""
    pts = [np.array(p, dtype=float) for p in pts]
    d = Dot(radius=r, color=color).move_to(pts[0]).set_z_index(8)
    path = VMobject().set_points_as_corners(pts)
    return Succession(FadeIn(d, run_time=0.04), MoveAlongPath(d, path, rate_func=smooth, run_time=rt), FadeOut(d, run_time=0.1))


def code_panel(title, lines, x):
    r = RoundedRectangle(corner_radius=0.14, width=6.5, height=3.9, stroke_color=GREY_B, stroke_width=2.5).set_fill("#0b0d10", 1)
    r.move_to([x, 0.45, 0])
    head = left_at(T(title, 22, GREY_B), x - 3.0, 2.08)
    rows = VGroup()
    for k, s in enumerate(lines):
        col = GREY_B if s.strip().startswith("//") else WHITE
        ind = (len(s) - len(s.lstrip())) * M("x" * 40, 14).width / 40
        rows.add(left_at(M(s.strip() if s.strip() else " ", 14, col), x - 3.0 + ind, 1.55 - 0.4 * k))
    return VGroup(r, head, rows).set_z_index(10)




def page(name, line1, line2=None, color=WHITE):
    r = RoundedRectangle(corner_radius=0.1, width=PG_W, height=PG_H, stroke_color=color, stroke_width=3).set_fill(fillc(color, 0.1), 1)
    rows = [T(f"page {name}", 24, color), T(line1, 19, GREY_B)]
    if line2:
        rows.append(M(line2, 18, color))
    g = VGroup(*rows).arrange(DOWN, buff=0.1).move_to(r)
    return VGroup(r, g)


def proc(box, title, color):
    r = frame(box[0], box[1], box[2], box[3], color)
    t = T(title, 26, color).move_to([cx(box), box[2] - 0.34, 0])
    return VGroup(r, t)


def table(box, color):
    cells = VGroup(*[VGroup(Square(0.42, stroke_color=color, stroke_width=2).set_fill(BLACK, 1), M(n, 19, color))
                     for n in "ABC"]).arrange(RIGHT, buff=0.06)
    for c in cells:
        c[1].move_to(c[0])
    lab = T("page table", 17, GREY_B)
    g = VGroup(lab, cells).arrange(RIGHT, buff=0.18).move_to([cx(box), box[3] + 0.36, 0])
    return g


JAVA = ["// BGSAVE: fork, then answer at once",
        "redis.executeCommand(",
        "    new CommandArguments(Protocol.Command.BGSAVE));",
        "// how long the fork took, in microseconds",
        "long fork = stat(redis, \"stats\", \"latest_fork_usec\");",
        "// bytes of pages copied during the save",
        "long cow = stat(redis, \"persistence\",",
        "    \"rdb_last_cow_size\");"]
KOTLIN = ["// BGSAVE: fork, then answer at once",
          "redis.executeCommand(",
          "    CommandArguments(Protocol.Command.BGSAVE))",
          "// how long the fork took, in microseconds",
          "val fork = redis.stat(\"stats\", \"latest_fork_usec\")",
          "// bytes of pages copied during the save",
          "val cow = redis.stat(\"persistence\",",
          "    \"rdb_last_cow_size\")"]


class RdbAof(Base):
    """cache-09, section 1. Redis's data lives in memory; a snapshot copies it to dump.rdb. SAVE runs on the one
    thread: 83 MB took 2,065 ms and a GET waited 1,761 ms. The café's whiteboard and its photographer. A helper
    copying while writes go on would mix moments. BGSAVE: fork() makes a child; it copies only the page table (pages of
    4 KB). Predict what fork copies. Copy-on-write: SET payment:5 refunded makes the kernel copy page B for the parent;
    the child keeps the old B. temp-41.rdb renamed to dump.rdb in one step; the child exits; B is freed. Costs: the
    page table (8 bytes per 4 KB page, 48 MB for 24 GB, 10 to 25 ms per GB; 6 to 31 ms for 83 MB in the lab) and the
    copied pages (3 to 5 MB in the lab, up to twice memory). A crash loses the writes after the fork. Code in Java and
    Kotlin, the moral, a check (three writes to payment 5: one copy)."""

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color), 13.0).move_to([0, CAP_Y, 0])
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def put(self, key, mob, d=UP):
        old = self.lab.get(key)
        self.lab[key] = mob
        return [swap(old, mob, d)]

    def drop(self, *keys):
        out = []
        for key in keys:
            old = self.lab.pop(key, None)
            if old is not None:
                out.append(FadeOut(old))
        return out

    def status(self, who, s, color=GREY_B):
        box = PA if who == "pa" else CH
        return self.put("st_" + who, T(s, 20, color).move_to([cx(box), box[2] - 0.78, 0]))

    def disk(self, s, color=WHITE):
        return self.put("dk", M(s, 22, color).move_to([cx(DK), -2.05, 0]))

    def disk_note(self, s, color=GREY_B):
        return self.put("dkn", T(s, 17, color).move_to([cx(DK), -2.45, 0]))

    def countdown(self, secs=3.0):
        bar = Line([-1.0, BAR_Y, 0], [1.0, BAR_Y, 0], stroke_width=5, color=YELLOW_M)
        self.play(Create(bar), run_time=0.25)
        self.play(Uncreate(bar), run_time=secs, rate_func=linear)

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("A photo of memory, without stopping", "fork, copy-on-write, and the snapshot file")

        pa = proc(PA, "Redis (the parent)", BLUE_M)
        pages = {k: page(k, f"payments {3 * i + 1}-{3 * i + 3}", "p:5 settled" if k == "B" else None).move_to([PG_X[k], PG_Y, 0])
                 for i, k in enumerate("ABC")}
        top = {k: np.array([PG_X[k], PG_Y + PG_H / 2 + 0.06, 0]) for k in "ABC"}
        p_lines = {k: Line([PA[0] + 1.0 + 0.4 * i, PA[3] - 0.04, 0], top[k], stroke_width=2.5, color=BLUE_M)
                   for i, k in enumerate("ABC")}
        dk = frame(DK[0], DK[1], DK[2], DK[3], GREY_B)
        dk_t = T("disk", 20, GREY_B).move_to([DK[0] + 0.45, DK[2] - 0.3, 0])
        ptab = table(PA, BLUE_M)

        # ---------------- scene 1: the question ----------------
        self.steps("Redis keeps all its data in memory, and memory is wiped when a program stops. "
                   "So now and then, Redis writes a copy of everything to a file on disk: a snapshot.", [
            (lambda: [FadeIn(pa), *self.status("pa", "serves clients"), *[FadeIn(pages[k]) for k in "ABC"],
                      *[Create(p_lines[k]) for k in "ABC"]], 1.0),
            "memory is wiped",
            (lambda: [*[pages[k].animate(rate_func=there_and_back).set_opacity(0.15) for k in "ABC"]], 1.0),
            "a file on disk",
            (lambda: [FadeIn(dk), FadeIn(dk_t), *self.disk("dump.rdb"), *self.cap("a snapshot: dump.rdb")], 0.7),
        ])
        self.steps("But Redis runs every command on one thread, one path of work. "
                   "So how can it copy gigabytes to disk without making every client wait?", [
            (lambda: [*self.cap("one thread runs every command"), glow(pa[0], BLUE_M, 1.02)], 0.8),
            "So how",
            (lambda: self.cap("how do you copy gigabytes without making every client wait?", WHITE), 0.5),
        ])

        # ---------------- scene 2: SAVE ----------------
        def to_disk(k, color=WHITE, rt=0.6):
            return run_pts([pages[k].get_bottom() + 0.05 * DOWN, [cx(DK) - 1.0 + 0.6 * "ABC".index(k), DK[2] + 0.05, 0]], color, rt)

        self.steps("The plain way is the command SAVE: the main thread writes the file itself. "
                   "In the lab, a million payments, 83 megabytes, took 2,065 milliseconds to save.", [
            (lambda: self.cap("SAVE: the main thread writes the file itself"), 0.5),
            "writes the file",
            (lambda: [*self.status("pa", "busy: writing a file", RED_M),
                      LaggedStart(*[to_disk(k) for k in "ABCABC"], lag_ratio=0.3)], 2.0),
            "In the lab",
            (lambda: self.cap("1,000,000 payments, 83 MB: SAVE took 2,065 ms"), 0.5),
        ])
        client = chip("a client: GET", GREY_B, 22).move_to([0, 2.5, 0])
        self.steps("A client that asked for one key 200 milliseconds in waited 1,761 milliseconds for its answer. "
                   "Nothing else ran, because the only thread that runs commands was busy writing a file.", [
            (lambda: [FadeIn(client, shift=0.1 * DOWN)], 0.5),
            "waited",
            (lambda: [*self.cap("a GET sent 200 ms in: it waited 1,761 ms", RED_M), Indicate(client, color=RED_M)], 0.8),
            "Nothing else ran",
            (lambda: [glow(pa[0], RED_M, 1.02)], 0.8),
        ])
        self.steps("With 25 gigabytes, that pause would last minutes.", [
            (lambda: [*self.cap("25 GB: a pause of minutes", RED_M), FadeOut(client), *self.status("pa", "serves clients")], 0.6),
        ], after=0.3)

        # ---------------- scene 3: the café ----------------
        self.steps("Think of a café that keeps today's orders on a whiteboard. Wipe the board and they're gone, "
                   "so now and then you take a photo of it.", [
            (lambda: self.cap("a café's whiteboard of orders: memory"), 0.5),
            "take a photo",
            (lambda: self.cap("a photo of the board: the snapshot"), 0.5),
        ])
        self.steps("SAVE is a photographer who makes the staff stop writing until he has copied the whole board by hand.", [
            (lambda: [*self.cap("SAVE: everyone stops until the copy is done", RED_M)], 0.5),
        ], after=0.3)
        self.steps("So let a helper copy the board while the staff keep writing? Then the copy mixes moments: "
                   "payment 5 from ten o'clock, payment 900,000 from two seconds later.", [
            (lambda: self.cap("a helper copying while writes go on?", PURPLE_M), 0.5),
            "mixes moments",
            (lambda: [*self.cap("payment 5 from 10:00:00, payment 900,000 from 10:00:02", PURPLE_M),
                      pages["A"].animate(rate_func=there_and_back).set_color(YELLOW_M)], 0.9),
        ])
        self.steps("A refund could land in the file without the payment it refunds. "
                   "We need both: someone else does the copying, and the copy still shows one moment.", [
            (lambda: self.cap("a refund in the file, without its payment", RED_M), 0.5),
            "We need both",
            (lambda: self.cap("someone else copies, and the copy shows one moment", YELLOW_M), 0.5),
        ])

        # ---------------- scene 4: fork ----------------
        ch = proc(CH, "the child", TEAL_M)
        self.steps("Redis's answer is BGSAVE, a background save. The main thread calls fork: a request to the kernel, "
                   "the core of the operating system, to copy the running program.", [
            (lambda: self.cap("BGSAVE: a background save"), 0.5),
            "calls fork",
            (lambda: [*self.cap("fork(): ask the kernel to copy the running program"), glow(pa[0], BLUE_M, 1.02)], 0.8),
        ])
        self.steps("The original is the parent, and the copy is the child. The child will write the file, "
                   "and the parent goes on serving clients.", [
            "the child",
            (lambda: [FadeIn(ch, shift=0.2 * RIGHT), *self.status("ch", "will write the file", TEAL_M)], 0.8),
            "the parent goes on",
            (lambda: [*self.status("pa", "serves clients", GREEN_M)], 0.5),
        ])
        self.steps("But copying 25 gigabytes of memory would take seconds too. So what does fork actually copy? Pause and guess.", [
            (lambda: self.cap("copying 25 GB takes seconds too", RED_M), 0.5),
            "Pause and guess",
            (lambda: self.cap("what does fork copy? pause and guess", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        c_lines = {k: DashedLine([CH[1] - 1.0 - 0.4 * (2 - i), CH[3] - 0.04, 0], top[k], dash_length=0.1, stroke_width=2.5, color=TEAL_M)
                   for i, k in enumerate("ABC")}
        ctab = table(CH, TEAL_M)
        self.steps("Almost nothing. Memory is handed out in pages, blocks of 4 kilobytes, and each program has a page table, "
                   "the kernel's map from its addresses to pages.", [
            (lambda: self.cap("almost nothing", WHITE, 30), 0.5),
            "in pages",
            (lambda: [*[glow(pages[k][0], WHITE, 1.04) for k in "ABC"], *self.cap("pages: blocks of 4 KB")], 0.8),
            "a page table",
            (lambda: [FadeIn(ptab), *self.cap("the page table: the map from addresses to pages")], 0.6),
        ])
        self.steps("Fork copies only the map. Parent and child point at the same pages. "
                   "In the café, the photographer gets a list of the board's panels; no panel moves.", [
            (lambda: [TransformFromCopy(ptab, ctab)], 1.0),
            "point at the same",
            (lambda: [*[Create(c_lines[k]) for k in "ABC"], *self.cap("fork copies the map, not the pages")], 0.9),
            "In the café",
            (lambda: [a for k in "ABC" for a in self.put("sh" + k, T("shared", 17, GREY_B).next_to(pages[k], DOWN, buff=0.08))], 0.6),
        ])
        self.steps("The child writes every key to a temporary file, and the parent serves clients at full speed.", [
            (lambda: [*self.disk("temp-41.rdb", TEAL_M), *self.status("ch", "writing temp-41.rdb", TEAL_M)], 0.6),
            (lambda: [LaggedStart(*[to_disk(k, TEAL_M) for k in "ABC"], lag_ratio=0.3)], 1.4),
        ])
        self.stamp("fork")

        # ---------------- scene 5: copy-on-write ----------------
        bp = page("B'", "payments 4-6", "p:5 refunded", GOLD_M).move_to(BP)
        bp_old = page("B'", "payments 4-6", "p:5 settled", GOLD_M).move_to(BP)
        bp_line = VMobject(stroke_width=2.5, color=BLUE_M).set_points_as_corners(
            [[PA[0] + 1.4, PA[3] - 0.04, 0], [PA[0] + 1.4, BP[1], 0], [BP[0] - PG_W / 2 - 0.06, BP[1], 0]])
        cmd = chip("SET payment:5 refunded", GOLD_M, 22).move_to([0, 2.5, 0])
        self.steps("Now a client changes payment 5 to refunded. It lives on page B, which the child still needs.", [
            (lambda: [FadeIn(cmd, shift=0.1 * DOWN)], 0.5),
            "page B",
            (lambda: [glow(pages["B"][0], GOLD_M, 1.04)], 0.8),
            "the child still needs",
            (lambda: [Indicate(c_lines["B"], color=TEAL_M)], 0.6),
        ])
        self.steps("So the kernel first copies page B, and gives the copy to the parent. The parent writes refunded on its copy.", [
            "copies page B",
            (lambda: [TransformFromCopy(pages["B"], bp_old)], 0.9),
            "gives the copy",
            (lambda: [FadeOut(p_lines["B"]), Create(bp_line)], 0.7),
            "writes refunded",
            (lambda: [ReplacementTransform(bp_old, bp)], 0.5),
        ])
        self.steps("The child still sees page B as it was, with payment 5 settled. Its picture stays frozen at the moment of the fork.", [
            (lambda: [*self.put("shB", T("child only", 17, TEAL_M).next_to(pages["B"], DOWN, buff=0.08)), Indicate(pages["B"][1][2], color=TEAL_M)], 0.8),
            "frozen",
            (lambda: self.cap("the child's picture: frozen at the fork", TEAL_M), 0.5),
        ])
        self.steps("That's copy-on-write: a page is copied only when someone is about to change it. "
                   "In the café, a waiter about to write on a panel first swaps in a fresh copy, and the photographer keeps the old one.", [
            (lambda: [FadeOut(cmd), *self.cap("copy-on-write: copy a page only when it's about to change", GOLD_M, 28)], 0.6),
            "In the café",
            (lambda: [glow(bp[0], GOLD_M, 1.04)], 0.8),
        ])
        self.steps("Everyone's happy, except the memory chips, which now hold one page twice.", [
            (lambda: [Indicate(pages["B"], color=WHITE, scale_factor=1.04), Indicate(bp, color=WHITE, scale_factor=1.04)], 1.0),
        ], after=0.3)

        # ---------------- scene 6: finish, and the costs ----------------
        self.steps("When the child finishes, it renames its file to dump.rdb. A rename happens in one step, "
                   "so a crash halfway leaves the old snapshot, never half of a new one.", [
            (lambda: [*self.disk("dump.rdb", WHITE), *self.status("ch", "done: rename", TEAL_M)], 0.6),
            "A rename",
            (lambda: [*self.cap("rename: one step, so never half a snapshot"), *self.disk_note("the data at the moment of the fork")], 0.6),
        ])
        self.steps("Then the child exits, and the old page B, which only the child used, is freed.", [
            (lambda: [*[FadeOut(c_lines[k]) for k in "ABC"], FadeOut(ch), FadeOut(ctab), *self.drop("st_ch")], 0.8),
            "is freed",
            (lambda: [pages["B"].animate.set_opacity(0.2), *self.put("shB", T("freed", 17, GREY_B).next_to(pages["B"], DOWN, buff=0.08)),
                      *self.drop("shA", "shC")], 0.6),
        ])
        self.stamp("poster")
        self.steps("In the lab, forking 83 megabytes took 6 to 31 milliseconds, instead of a two-second stop.", [
            (lambda: self.cap("the lab: fork of 83 MB took 6 to 31 ms, instead of 2,065 ms", GREEN_M), 0.6),
        ], after=0.3)
        self.steps("Two costs remain, and both fall on the parent. The fork still copies the page table: 8 bytes for every 4 kilobyte page. "
                   "A 24 gigabyte Redis copies 48 megabytes of table, at about 10 to 25 milliseconds per gigabyte on most machines.", [
            (lambda: [self.cap("cost 1: the fork copies the page table", WHITE)[0], Indicate(ptab, color=BLUE_M)], 0.6),
            "A 24 gigabyte",
            (lambda: self.cap("24 GB / 4 KB x 8 bytes = 48 MB of table: about 10 to 25 ms per GB"), 0.6),
        ])
        self.steps("And every page the parent changes during the save gets copied. In the lab, a few hundred updates copied 3 to 5 megabytes. "
                   "On a server that writes heavily, it can come close to twice the memory.", [
            (lambda: [*self.cap("cost 2: every page changed during the save gets copied", WHITE), glow(bp[0], GOLD_M, 1.04)], 0.6),
            "In the lab",
            (lambda: self.cap("the lab: a few hundred updates copied 3 to 5 MB"), 0.5),
            "close to twice",
            (lambda: self.cap("heavy writes: close to twice the memory", RED_M), 0.5),
        ])
        self.steps("So keep Redis's memory limit well below the machine's memory.", [
            (lambda: self.cap("keep maxmemory well below the machine's RAM", YELLOW_M), 0.5),
        ], after=0.3)

        # ---------------- scene 7: what a crash loses ----------------
        self.steps("And a snapshot is only as new as its fork. With the default rules, a busy server saves about once a minute, "
                   "so a crash loses about a minute of writes.", [
            (lambda: self.cap("a snapshot is only as new as its fork"), 0.5),
            "a crash loses",
            (lambda: self.cap("default rules, busy server: a crash loses about a minute of writes", RED_M), 0.5),
        ])
        self.steps("Kill Redis now, and the restart loads dump.rdb. Payment 5 is settled again; the refund after the fork is gone.", [
            (lambda: [*self.status("pa", "killed: kill -9", RED_M), pa[0].animate.set_stroke(RED_M)], 0.6),
            "the restart loads",
            (lambda: [FadeOut(bp), FadeOut(bp_line), pages["B"].animate.set_opacity(1), Create(p_lines["B"]),
                      *self.drop("shB"), pa[0].animate.set_stroke(BLUE_M), *self.status("pa", "restarted from dump.rdb", GREY_B),
                      LaggedStart(*[run_pts([[cx(DK) - 1.0 + 0.6 * i, DK[2] + 0.05, 0], pages[k].get_bottom() + 0.05 * DOWN], WHITE, 0.5)
                                    for i, k in enumerate("ABC")], lag_ratio=0.3)], 1.4),
            "the refund",
            (lambda: [Indicate(pages["B"][1][2], color=RED_M), *self.cap("p:5 settled again: the refund after the fork is lost", RED_M)], 0.8),
        ])
        self.steps("For a cache, that's fine: it refills from the database. For the café's payment notes, it isn't.", [
            (lambda: self.cap("a cache: fine, it refills.   payment notes: not fine"), 0.5),
        ], after=0.3)

        # ---------------- scene 8: the code ----------------
        diagram = VGroup(*[m for m in self.mobjects if m is not self.capm and isinstance(m, VMobject)])
        diagram.save_state()
        jp = code_panel("Java", JAVA, -3.35)
        kp = code_panel("Kotlin", KOTLIN, 3.35)

        def hl(rows, color):
            return [p[2][r].animate(rate_func=there_and_back).set_color(color) for p in (jp, kp) for r in rows]

        self.steps("In Java and Kotlin, BGSAVE is one command, and Redis answers as soon as it has forked. "
                   "Its stats then tell you how long the fork took, and how much the kernel copied.", [
            (lambda: [*self.uncap(), diagram.animate.set_opacity(0.06)], 0.6),
            (lambda: [FadeIn(jp, shift=0.1 * UP), FadeIn(kp, shift=0.1 * UP)], 0.7),
            "BGSAVE is one",
            (lambda: hl((1, 2), TEAL_M), 1.3),
            "how long the fork",
            (lambda: hl((4,), BLUE_M), 1.1),
            "how much the kernel",
            (lambda: hl((6, 7), GOLD_M), 1.1),
        ], after=0.5)

        # ---------------- scene 9: the moral, and a check ----------------
        self.steps("So, how does Redis photograph its memory without stopping? It forks. The child gets the picture, the parent "
                   "keeps working, and the kernel copies a page only when the parent is about to change it.", [
            (lambda: [FadeOut(jp), FadeOut(kp), Restore(diagram)], 0.8),
            "It forks",
            (lambda: self.cap("fork: the child gets the picture, the parent keeps working", WHITE), 0.5),
            "and the kernel",
            (lambda: self.cap("copy a page only when it's about to change", GOLD_M, 30), 0.5),
        ], after=0.4)
        self.steps("One quick check. During a save, the parent changes payment 5 three times. "
                   "How many copies of page B does the kernel make? Pause and think.", [
            (lambda: [*self.uncap(), *self.status("pa", "serves clients", GREEN_M)], 0.4),
            "three times",
            (lambda: [Indicate(pages["B"], color=GOLD_M, scale_factor=1.04)], 0.7),
            "Pause and think",
            (lambda: self.cap("three writes to page B: how many copies? pause and think", YELLOW_M), 0.4),
        ], after=0)
        self.countdown(3.0)
        self.steps("One. After the first copy, page B prime belongs to the parent alone, so the next writes go straight to it.", [
            (lambda: [FadeOut(p_lines["B"]), Create(bp_line), FadeIn(bp)], 0.7),
            "the next writes",
            (lambda: [*self.cap("one copy: after that, B' is the parent's alone", YELLOW_M),
                      *[glow(bp[0], GOLD_M, 1.04) for _ in range(1)]], 0.8),
        ])
        self.steps("Next, to lose less than a minute, the café's notebook: a log of every change.", [
            (lambda: self.cap("next: a log of every change", WHITE), 0.5),
        ], after=0.3)
        self.wait(2.0)
