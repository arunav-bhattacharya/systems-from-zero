from sfz import *

SAY.insert(0, (r"\bdump\.rdb\b", "dump dot R D B"))
SAY.insert(0, (r"\bBGSAVE\b", "B G save"))
SAY.insert(0, (r"\bSAVE\b", "save"))
SAY.insert(0, (r"\bGET\b", "get"))
SAY.insert(0, (r"\bfsynced\b", "eff synced"))

PX, PY, PW = -1.4, 2.9, 5.4                 # parent process box
CY = -1.7                                    # child process box
GY, GS = 0.4, 0.7                            # the row of memory pages and their size
XS = [-3.65 + 0.9 * i for i in range(6)]
KX, KY = 4.35, 2.9                           # client
DX, DY, DW, DH = 4.35, -1.8, 4.1, 1.7        # disk
F_DUMP, F_TEMP, F_AOF = (3.15, -1.45), (3.15, -2.2), (5.15, -1.45)
PCX, PCY = 4.35, 0.5                         # kernel page cache
ST = (-1.4, -3.05)                           # status line


def glow(rect, color=YELLOW_M, s=1.03):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def flow(path, color=YELLOW_M, run_time=1.0, back=False):
    """A dot that runs along an arrow (or back along it) and stays invisible until its turn."""
    a, b = (path.get_end(), path.get_start()) if back else (path.get_start(), path.get_end())
    d = Dot(radius=0.07, color=color).move_to(a).set_opacity(0)
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, Line(a, b), rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


def fill(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


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


def proc(label, y, color=WHITE, lcolor=WHITE):
    r = RoundedRectangle(corner_radius=0.14, width=PW, height=0.8, stroke_color=color, stroke_width=3)
    r.set_fill(BLACK if ManimColor(color).to_hex().upper() == "#FFFFFF" else fill(color), 1).move_to([PX, y, 0])
    return VGroup(r, T(label, 22, lcolor).move_to([PX, y, 0]))


def page(i, color=GREY_B, y=GY, name=None):
    sq = Square(GS, stroke_color=color, stroke_width=2.5).set_fill(fill(color, 0.2), 1).move_to([XS[i], y, 0])
    return VGroup(sq, M(name or str(i + 1), 18, WHITE).move_to(sq))


def fchip(name, xy, color=GREY_B):
    return chip(name, color, 16, mono=True).move_to([xy[0], xy[1], 0])


def status(s, color=GREY_B):
    return T(s, 20, color).move_to([ST[0], ST[1], 0])


class RdbAof(Base):
    """cache-09, sections 1 and 2: SAVE blocks the one thread (2,065 ms; a GET waits 1,761 ms). BGSAVE forks a child that
    shares every page; a write makes the kernel copy one 4 KB page, so the child's file is the instant of the fork; the
    temp file is renamed over dump.rdb. A crash loses every write since the snapshot. The AOF appends each write; it
    reaches the page cache at once and the disk at the fsync each second, so a dead process loses nothing and a dead
    machine about a second."""

    def construct(self):
        self.title_card("Saving Redis to disk", "a forked snapshot, and a log of every write")

        par = proc("Redis: the main thread", PY)
        pages = [page(i) for i in range(6)]
        pl = [Line([x, PY - 0.4, 0], [x, GY + GS / 2 + 0.03, 0], stroke_width=2, color=GREY_D) for x in XS]
        mem = VGroup(T("memory", 22, GREY_B), T("3 million keys", 17, GREY_B)).arrange(DOWN, buff=0.14).move_to([-5.45, GY, 0])
        empty = chip("restarted: empty, so every retry looks new", RED_M, 19).move_to([ST[0], ST[1], 0])
        self.steps("Redis holds three million idempotency keys, all in memory. When the process restarts, "
                   "it comes back empty, and every retried payment looks new.", [
            (lambda: [FadeIn(par)], 0.6),
            (lambda: [*[Create(l) for l in pl], LaggedStart(*[FadeIn(p, scale=0.8) for p in pages], lag_ratio=0.12), FadeIn(mem)], 1.2),
            "When the process",
            (lambda: [*[p.animate.set_opacity(0.08) for p in pages], par[0].animate.set_stroke(RED_M)], 0.8),
            "and every retried",
            (lambda: [FadeIn(empty, shift=0.1 * UP)], 0.7),
            0.5,
            (lambda: [*[p.animate.set_opacity(1) for p in pages], par[0].animate.set_stroke(WHITE), FadeOut(empty)], 0.6),
        ])

        disk = RoundedRectangle(corner_radius=0.14, width=DW, height=DH, stroke_color=GREY_B, stroke_width=2.5)
        disk.set_fill(BLACK, 1).move_to([DX, DY, 0])
        disk_l = T("disk", 19, GREY_B).move_to([F_AOF[0], F_TEMP[1], 0])
        dump = fchip("dump.rdb", F_DUMP)
        cli = box("client", WHITE, w=1.8, h=0.8, size=22).move_to([KX, KY, 0])
        get = Arrow([KX - 0.95, KY, 0], [PX + PW / 2 + 0.08, KY, 0], buff=0, stroke_width=3, color=GREY_B,
                    max_tip_length_to_length_ratio=0.15)
        get_l = M("GET", 17, GREY_B).next_to(get, UP, buff=0.1)
        sv = Arrow([PX + PW / 2 - 0.3, PY - 0.42, 0], [F_DUMP[0] - 0.1, F_DUMP[1] + 0.36, 0], buff=0, stroke_width=3,
                   color=GOLD_M, max_tip_length_to_length_ratio=0.05)
        wait = T("GET waits 1,761 ms", 19, RED_M).move_to([KX, KY - 0.7, 0])
        stuck = Dot(radius=0.08, color=RED_M).move_to(get.get_end() + 0.15 * RIGHT)
        self.steps("The simplest copy is SAVE, which writes every key to a file on the one command thread. "
                   "In the lab that took two seconds, and a GET sent meanwhile waited 1.8 seconds.", [
            (lambda: [FadeIn(disk), FadeIn(disk_l), FadeIn(dump)], 0.7),
            "on the one",
            (lambda: [GrowArrow(sv), Transform(par[1], T("SAVE: busy writing the file", 22, GOLD_M).move_to(par[1]))], 0.8),
            (lambda: [LaggedStart(*[flow(sv, GOLD_M, 0.6) for _ in range(3)], lag_ratio=0.4)], 1.2),
            "and a GET",
            (lambda: [FadeIn(cli), GrowArrow(get), FadeIn(get_l)], 0.6),
            (lambda: [FadeIn(stuck), FadeIn(wait, shift=0.1 * DOWN), Transform(par[1], T("SAVE: 2,065 ms", 22, RED_M).move_to(par[1]))], 0.7),
        ])

        chi = proc("child: writes the snapshot", CY, TEAL_M, TEAL_M)
        cl = [Line([x, GY - GS / 2 - 0.03, 0], [x, CY + 0.4, 0], stroke_width=2, color=TEAL_M) for x in XS]
        fk = T("fork()", 19, TEAL_M, ).move_to([-5.45, CY, 0])
        self.steps("BGSAVE hands the job to a child. The main thread calls fork, and the kernel copies only the page table, "
                   "so both processes point at the same pages.", [
            (lambda: [FadeOut(sv), FadeOut(stuck), FadeOut(wait), Transform(par[1], T("parent: serves clients", 22).move_to(par[1]))], 0.7),
            "The main thread",
            (lambda: [FadeIn(chi, shift=0.2 * DOWN), FadeIn(fk)], 0.8),
            "the page table",
            (lambda: [*[Create(l) for l in cl]], 0.8),
            "so both",
            (lambda: [*[l.animate(rate_func=there_and_back).set_stroke(width=5) for l in pl + cl],
                      *[glow(p[0], WHITE, 1.06) for p in pages]], 1.0),
        ])

        temp = fchip("temp.rdb", F_TEMP, TEAL_M)
        cw = Arrow([PX + PW / 2 + 0.06, CY, 0], [F_TEMP[0] - 0.72, F_TEMP[1] + 0.08, 0], buff=0, stroke_width=3, color=TEAL_M,
                   max_tip_length_to_length_ratio=0.15)
        self.steps("The child writes those pages to a file, while the parent keeps serving clients.", [
            (lambda: [GrowArrow(cw), FadeIn(temp)], 0.7),
            (lambda: [LaggedStart(*[flow(cw, TEAL_M, 0.5) for _ in range(3)], lag_ratio=0.5)], 1.2),
            "while the parent",
            (lambda: [flow(get, WHITE, 0.5), LaggedStart(*[flow(cw, TEAL_M, 0.5) for _ in range(2)], lag_ratio=0.5)], 0.9),
            (lambda: [flow(get, GREEN_M, 0.5, back=True)], 0.6),
        ])

        cp = page(2, GOLD_M, y=1.62, name="3")
        pl2 = Line([XS[2], PY - 0.4, 0], [XS[2], 1.62 + GS / 2 + 0.03, 0], stroke_width=2, color=GOLD_M)
        cowl = T("copy, 4 KB", 18, GOLD_M).next_to(cp, LEFT, buff=0.2)
        self.steps("Now a client changes a key on page three. The kernel first copies that one 4 kilobyte page, "
                   "and the parent writes to its copy.", [
            (lambda: [Transform(get_l, M("SET", 17, GOLD_M).move_to(get_l))], 0.4),
            (lambda: [flow(get, GOLD_M, 0.6), glow(pages[2][0], GOLD_M, 1.08)], 0.8),
            "The kernel first",
            (lambda: [FadeIn(cp, shift=0.5 * UP), FadeIn(cowl)], 0.8),
            "and the parent",
            (lambda: [ReplacementTransform(pl[2], pl2)], 0.6),
            (lambda: [cp[0].animate.set_fill(fill(GOLD_M, 0.5), 1), Transform(cp[1], M("3*", 18, WHITE).move_to(cp))], 0.6),
        ])
        pl[2] = pl2

        old = T("the child still reads the old page", 18, TEAL_M).move_to([XS[2] + 0.2, CY - 0.7, 0])
        self.steps("The child still sees the old page, so its file shows the moment of the fork. "
                   "That's copy-on-write, and only pages written during the save get copied.", [
            (lambda: [cl[2].animate.set_stroke(width=5), glow(pages[2][0], TEAL_M, 1.08), FadeIn(old)], 0.9),
            "so its file",
            (lambda: [flow(cw, TEAL_M, 0.6), glow(temp[0], TEAL_M, 1.05)], 0.8),
            "That's copy-on-write",
            (lambda: [glow(cp[0], GOLD_M, 1.08)], 0.8),
        ])

        new_dump = fchip("dump.rdb", F_DUMP, TEAL_M)
        atom = T("rename: one atomic step", 18, TEAL_M).move_to([DX, DY - DH / 2 - 0.3, 0])
        self.steps("When it's done, the child renames its file over dump.rdb in one step, "
                   "so a crash never leaves half a snapshot.", [
            (lambda: [FadeOut(old), cl[2].animate.set_stroke(width=2)], 0.4),
            "renames",
            (lambda: [FadeOut(dump), ReplacementTransform(temp, new_dump)], 0.9),
            (lambda: [FadeIn(atom)], 0.5),
            "so a crash",
            (lambda: [FadeOut(cw), FadeOut(chi), FadeOut(fk), *[FadeOut(l) for l in cl], FadeOut(pages[2]), FadeOut(cowl)], 0.8),
            (lambda: [cp.animate.move_to([XS[2], GY, 0]),
                      Transform(pl[2], Line([XS[2], PY - 0.4, 0], [XS[2], GY + GS / 2 + 0.03, 0], stroke_width=2, color=GREY_D))], 0.7),
        ])
        dump = new_dump
        pages[2] = cp

        often = chip("a snapshot about once a minute", GREY_B, 19).move_to([PX, CY, 0])
        lost = chip("50 seconds of writes: gone", RED_M, 19).move_to([ST[0], ST[1], 0])
        ld = Arrow([F_DUMP[0] - 0.7, F_DUMP[1] + 0.2, 0], [XS[5] + GS / 2 + 0.12, GY - 0.1, 0], buff=0, stroke_width=3,
                   color=TEAL_M, max_tip_length_to_length_ratio=0.12)
        crash = tick(False, 0.4).move_to([PX + PW / 2 - 0.45, PY, 0])
        self.steps("On a busy server a snapshot runs about once a minute. "
                   "Crash fifty seconds after one, and those fifty seconds of writes are gone.", [
            (lambda: [FadeOut(atom), FadeIn(often, shift=0.1 * UP), Transform(dump[1], M("dump.rdb", 16).move_to(dump[1]))], 0.8),
            "Crash fifty",
            (lambda: [Create(crash), *[p.animate.set_opacity(0.08) for p in pages], par[0].animate.set_stroke(RED_M)], 0.8),
            (lambda: [FadeOut(crash), par[0].animate.set_stroke(WHITE), GrowArrow(ld)], 0.6),
            (lambda: [flow(ld, TEAL_M, 0.6), *[pages[i].animate.set_opacity(1) for i in (0, 1, 3, 4, 5)],
                      Transform(pages[2], page(2))], 0.8),
            "those fifty",
            (lambda: [FadeIn(lost, shift=0.1 * UP), glow(pages[2][0], RED_M, 1.1)], 0.8),
        ])

        aof = fchip("appendonly.aof", F_AOF, GREEN_M)
        ap = Arrow([PX + PW / 2 - 0.15, PY - 0.42, 0], [F_AOF[0] - 0.4, F_AOF[1] + 0.36, 0], buff=0, stroke_width=3,
                   color=GREEN_M, max_tip_length_to_length_ratio=0.04)
        logl = M("SET idem:k42 ...", 16, GREEN_M).move_to([2.55, 1.15, 0]).rotate(0)
        self.steps("The append-only file logs every write as it happens, and Redis replays it on restart.", [
            (lambda: [FadeOut(lost), FadeOut(often), FadeOut(ld), Transform(get_l, M("SET", 17, GREEN_M).move_to(get_l))], 0.7),
            (lambda: [FadeIn(aof), GrowArrow(ap)], 0.7),
            "every write",
            (lambda: [flow(get, GREEN_M, 0.5)], 0.5),
            (lambda: [flow(ap, GREEN_M, 0.8), glow(aof[0], GREEN_M, 1.06)], 0.9),
            "and Redis replays",
            (lambda: [flow(ap, GREEN_M, 0.8, back=True)], 0.8),
        ])

        pc = RoundedRectangle(corner_radius=0.14, width=DW, height=0.9, stroke_color=BLUE_M, stroke_width=3)
        pc.set_fill(fill(BLUE_M), 1).move_to([PCX, PCY, 0])
        pct = T("kernel page cache", 21, BLUE_M).move_to([PCX, PCY + 0.18, 0])
        pcs = T("holds the last second of writes", 16, GREY_B).move_to([PCX, PCY - 0.2, 0])
        a1 = Arrow([PX + PW / 2 - 0.15, PY - 0.42, 0], [PCX - 1.3, PCY + 0.47, 0], buff=0, stroke_width=3, color=GREEN_M,
                   max_tip_length_to_length_ratio=0.1)
        w_l = M("write()", 16, GREEN_M).next_to(a1.get_center(), RIGHT, buff=0.2)
        a2 = Arrow([F_AOF[0], PCY - 0.47, 0], [F_AOF[0], F_AOF[1] + 0.36, 0], buff=0, stroke_width=3, color=BLUE_M,
                   max_tip_length_to_length_ratio=0.2)
        fs_l = T("fsync, once a second", 17, BLUE_M).next_to(a2, LEFT, buff=0.2)
        self.steps("But a write only reaches the kernel's page cache. Once a second, a background thread calls fsync, "
                   "and only then does the disk hold it.", [
            (lambda: [ReplacementTransform(ap, a1), FadeIn(pc), FadeIn(pct), FadeIn(w_l)], 0.9),
            (lambda: [flow(a1, GREEN_M, 0.6), FadeIn(pcs)], 0.7),
            "Once a second",
            (lambda: [GrowArrow(a2), FadeIn(fs_l)], 0.7),
            "and only then",
            (lambda: [flow(a2, BLUE_M, 0.6), glow(aof[0], BLUE_M, 1.06)], 0.8),
        ])

        ok1 = VGroup(tick(True, 0.2), T("process dies: the kernel still writes it out", 19, GREEN_M)).arrange(RIGHT, buff=0.2)
        ok1.move_to([PX, CY + 0.15, 0])
        no1 = VGroup(tick(False, 0.2), T("machine dies: up to the last second is gone", 19, RED_M)).arrange(RIGHT, buff=0.2)
        no1.move_to([PX, CY - 0.6, 0])
        pdead = tick(False, 0.4).move_to([PX + PW / 2 - 0.45, PY, 0])
        self.steps("If just the Redis process dies, the kernel still writes the page cache out, and nothing is lost. "
                   "If the machine dies, up to the last second is gone.", [
            (lambda: [Create(pdead), *[p.animate.set_opacity(0.08) for p in pages], par[0].animate.set_stroke(RED_M)], 0.8),
            "the kernel still",
            (lambda: [flow(a2, BLUE_M, 0.6), glow(pc, BLUE_M, 1.04)], 0.8),
            (lambda: [FadeIn(ok1, shift=0.1 * UP)], 0.6),
            "If the machine",
            (lambda: [pc.animate.set_stroke(RED_M).set_fill(fill(RED_M), 1), pct.animate.set_color(RED_M),
                      Transform(pcs, T("gone with the machine", 16, RED_M).move_to(pcs))], 0.8),
            (lambda: [FadeIn(no1, shift=0.1 * UP)], 0.6),
        ])

        self.steps("A snapshot loses every write since the last save. "
                   "The log, fsynced each second, loses at most about a second.", [
            (lambda: [FadeOut(pdead), *[p.animate.set_opacity(1) for p in pages], par[0].animate.set_stroke(WHITE),
                      pc.animate.set_stroke(BLUE_M).set_fill(fill(BLUE_M), 1), pct.animate.set_color(BLUE_M),
                      Transform(pcs, T("holds the last second of writes", 16, GREY_B).move_to(pcs))], 0.8),
            (lambda: [glow(dump[0], TEAL_M, 1.08)], 0.8),
            "The log",
            (lambda: [glow(aof[0], GREEN_M, 1.08), Indicate(no1, color=YELLOW_M, scale_factor=1.04)], 1.0),
        ])
        self.wait(0.6)
