from sfz import *

SAY.insert(0, (r"\bpg_basebackup\b", "P G base backup"))
SAY.insert(0, (r"\bpg_stat_replication\b", "P G stat replication"))
SAY.insert(0, (r"\bsynchronous_standby_names\b", "synchronous standby names"))
SAY.insert(0, (r"\bLSNs\b", "L S Ns"))
SAY.insert(0, (r"\bPatroni\b", "puh trow nee"))

PY, SY = 1.25, -1.1             # primary row, standby row
W, H, STEP, X0 = 0.72, 0.7, 0.82, -4.3
PX = 5.45                       # data pages column
AMTS = ["€40", "€12", "€99", "€7", "€25", "€18", "€80", "€54", "€63", "€31"]
BASE = 0x3A000000               # LSN of record 0; every record here is 0x200 bytes


def cx(i):
    return X0 + i * STEP


def bnd(k):
    """x of the boundary just after record k."""
    return cx(k) + STEP / 2


def lsn(k):
    v = BASE + (k + 1) * 0x200
    return f"{v >> 32:X}/{v & 0xFFFFFFFF:08X}"


class Base(VoiceScene):
    def add_mobjects_from_animations(self, animations):
        """Like Scene's, but never re-adds a group whose parts are already on screen (that would draw
        filled boxes over their own labels), and leaves introducers inside groups to add themselves on cue."""
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
        """Removing a group removes its parts too, even when the parts were added one by one."""
        fam = []
        for m in mobjects:
            fam.extend(m.get_family())
        return super().remove(*fam)

    def steps(self, text, steps, after=0.25):
        """Speak one line and play several animations one after another inside it. Each step is built
        just before it plays, so it starts from where the previous one ended."""
        path, dur = voice(text)
        self._cue(text, dur)
        self.add_sound(path)
        t = 0
        for fn, rt in steps:
            if fn is None:
                self.wait(rt)
            else:
                self.play(*fn(), run_time=rt)
            t += rt
        if dur - t > 0.02:
            self.wait(dur - t)
        if after:
            self.wait(after)


def flash(m, color, s=1.08):
    """Stroke-and-scale flash that keeps an opaque box's label visible."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color)


class PgReplication(Base):
    """sql-16: WAL first, a standby from a base backup streams and replays it, a replication slot, lag as LSNs,
    asynchronous commit, a crash and a promotion, and what synchronous commit saves."""

    def construct(self):
        self.title_card("Streaming replication", "and failover in PostgreSQL")

        def cell(row, i, color=WHITE):
            return mbox(AMTS[i], color, w=W, h=H, size=20).move_to([cx(i), row, 0])

        def rlabel(row, name, role, col):
            g = VGroup(T(name, 28), T(role, 22, col)).arrange(DOWN, buff=0.1).move_to([-5.75, row, 0])
            if g.get_left()[0] < -6.45:
                g.shift((-6.45 - g.get_left()[0]) * RIGHT)
            return g

        def pages(row, color=WHITE):
            return box("data pages", color, w=1.9, h=H, size=22).move_to([PX, row, 0])

        def side_arrow(row, word, col):
            a = Arrow([cx(9) + W / 2 + 0.1, row, 0], [PX - 0.95 - 0.08, row, 0], buff=0, stroke_width=3, color=col,
                      max_tip_length_to_length_ratio=0.25)
            lab = T(word, 20, col).next_to(a, UP, buff=0.12)
            return VGroup(a, lab)

        def wal_head(row, i0=0):
            return T("WAL", 20, GREY_B).move_to([cx(i0) - W / 2, row + H / 2 + 0.26, 0], aligned_edge=LEFT)

        prim = [cell(PY, i) for i in range(10)]
        stby = [cell(SY, i) for i in range(10)]
        p_lab = rlabel(PY, "primary", "read-write", BLUE_M)
        p_pages = pages(PY)
        p_head = wal_head(PY)
        p_later = side_arrow(PY, "later", GREY_B)

        # ---- one server ---------------------------------------------------------------------------------
        self.steps("One Postgres server holds every payment. If it dies, payments stop until someone restores a backup.", [
            (lambda: [FadeIn(p_lab), FadeIn(p_pages), FadeIn(p_head),
                      LaggedStart(*[FadeIn(c, shift=0.15 * RIGHT) for c in prim[:3]], lag_ratio=0.2)], 1.6),
            (None, 1.4),
            (lambda: [flash(VGroup(*prim[:3], p_pages), RED_M, 1.04)], 1.2),
        ])

        client = box("payments service", BLUE_M, size=26).move_to([-0.4, 3.0, 0])

        def commit_arrow(i, col=BLUE_M):
            return Arrow(client.get_bottom(), [cx(i), PY + H / 2 + 0.06, 0], buff=0.1, stroke_width=3, color=col,
                         max_tip_length_to_length_ratio=0.1)

        ca = commit_arrow(3)
        self.steps("Every change goes first to the write-ahead log, the WAL. A commit flushes the log to disk, "
                   "and the data page is written later.", [
            (lambda: [FadeIn(client, shift=0.2 * DOWN)], 0.8),
            (lambda: [GrowArrow(ca)], 0.7),
            (lambda: [FadeIn(prim[3], shift=0.3 * DOWN)], 0.7),
            (lambda: [flash(prim[3], YELLOW_M, 1.15)], 0.8),
            (None, 1.4),
            (lambda: [FadeOut(ca), FadeIn(p_later)], 0.8),
            (lambda: [flash(p_pages, YELLOW_M)], 0.9),
        ])

        s_lab = rlabel(SY, "standby", "read-only", TEAL_M)
        s_head = wal_head(SY, 4)
        self.steps("Replay that log onto a copy of the data, and you get a second, identical database: a standby.", [
            (lambda: [LaggedStart(*[flash(c, YELLOW_M, 1.12) for c in prim[:4]], lag_ratio=0.25)], 1.6),
            (None, 1.2),
            (lambda: [FadeIn(s_lab, shift=0.2 * UP)], 0.9),
        ])

        s_pages = pages(SY, TEAL_M)
        bb = Arrow(p_pages.get_bottom(), s_pages.get_top(), buff=0.1, stroke_width=3, color=TEAL_M,
                   max_tip_length_to_length_ratio=0.15)
        bb_l = M("pg_basebackup", 20, TEAL_M).next_to(bb, LEFT, buff=1.15)
        self.steps("pg_basebackup copies the data files over while the primary keeps running.", [
            (lambda: [GrowArrow(bb), FadeIn(bb_l)], 1.0),
            (lambda: [TransformFromCopy(p_pages, s_pages)], 1.4),
        ])

        s_replay = side_arrow(SY, "replay", TEAL_M)
        new45 = [prim[4], prim[5]]
        ca2 = commit_arrow(4)

        self.steps("The standby then connects to the primary, and streams the log as it's written. "
                   "It saves each record, and replays it onto its pages.", [
            (lambda: [FadeOut(bb), FadeOut(bb_l), FadeIn(s_head)], 0.6),
            (lambda: [GrowArrow(ca2), FadeIn(new45[0], shift=0.3 * DOWN)], 0.8),
            (lambda: [TransformFromCopy(prim[4], stby[4]), FadeOut(ca2)], 0.9),
            (lambda: [FadeIn(new45[1], shift=0.3 * DOWN)], 0.6),
            (lambda: [TransformFromCopy(prim[5], stby[5])], 0.9),
            (None, 1.0),
            (lambda: [FadeIn(s_replay)], 0.6),
            (lambda: [flash(s_pages, TEAL_M)], 0.8),
        ])

        # ---- the slot -----------------------------------------------------------------------------------
        slot_ln = DashedLine([bnd(5), PY + H / 2 + 0.12, 0], [bnd(5), PY - H / 2 - 0.12, 0], dash_length=0.08,
                             stroke_width=3, color=TEAL_M)
        slot_l = T("slot standby1", 22, TEAL_M).next_to(slot_ln, DOWN, buff=0.1)
        keep = Brace(VGroup(prim[6], prim[7]), UP, buff=0.1, color=TEAL_M)
        keep_l = T("kept for the standby", 20, TEAL_M).next_to(keep, UP, buff=0.08)
        down_lab = rlabel(SY, "standby", "restarting", GREY_B)
        self.steps("A replication slot remembers how far the standby has got. The primary keeps every record after that, "
                   "even while the standby is down, until its own disk fills.", [
            (lambda: [Create(slot_ln), FadeIn(slot_l)], 0.9),
            (lambda: [Transform(s_lab, down_lab), VGroup(*stby[4:6], s_pages, s_head, s_replay).animate.set_opacity(0.3)], 0.9),
            (lambda: [FadeIn(prim[6], shift=0.3 * DOWN)], 0.5),
            (lambda: [FadeIn(prim[7], shift=0.3 * DOWN)], 0.5),
            (lambda: [GrowFromCenter(keep), FadeIn(keep_l), VGroup(*prim[:4]).animate.set_opacity(0.35)], 0.9),
            (None, 2.2),
            (lambda: [flash(VGroup(prim[6], prim[7]), RED_M, 1.06), keep.animate.set_color(RED_M), keep_l.animate.set_color(RED_M)], 1.2),
        ])

        # ---- lag ----------------------------------------------------------------------------------------
        def marker(row, k, word, col, below=True):
            ln = DashedLine([bnd(k), row + H / 2 + 0.12, 0], [bnd(k), row - H / 2 - 0.12, 0], dash_length=0.08,
                            stroke_width=3, color=col)
            lab = T(word, 22, col).next_to(ln, DOWN if below else UP, buff=0.1)
            return VGroup(ln, lab)

        sent = marker(PY, 8, "sent", YELLOW_M)
        flushed = marker(SY, 7, "flushed", GOLD_M)
        replayed = marker(SY, 5, "replayed", TEAL_M)
        flight = cell(PY, 8, YELLOW_M).move_to([cx(8), -0.02, 0]).set_opacity(0.85)
        back_lab = rlabel(SY, "standby", "read-only", TEAL_M)
        gap = BraceBetweenPoints([bnd(5), SY - H / 2 - 0.72, 0], [bnd(7), SY - H / 2 - 0.72, 0], DOWN, color=GREY_B)
        gap_l = T("1,536 bytes behind", 22, GREY_B).next_to(gap, DOWN, buff=0.08)
        rd = VGroup(
            M("pg_stat_replication", 20, GREY_B),
            M(f"sent_lsn    {lsn(8)}", 20, YELLOW_M),
            M(f"flush_lsn   {lsn(7)}", 20, GOLD_M),
            M(f"replay_lsn  {lsn(5)}", 20, TEAL_M),
        ).arrange(DOWN, buff=0.14, aligned_edge=LEFT).move_to([4.6, -2.8, 0])
        self.steps("The standby catches up, but it stays a little behind. pg_stat_replication shows positions "
                   "in the log, called LSNs: how far the primary has sent, how far the standby has flushed, and how far it has replayed. "
                   "The gaps are the lag.", [
            (lambda: [FadeOut(keep), FadeOut(keep_l), FadeOut(slot_ln), FadeOut(slot_l), Transform(s_lab, back_lab),
                      VGroup(*stby[4:6], s_pages, s_head, s_replay).animate.set_opacity(1)], 0.9),
            (lambda: [TransformFromCopy(prim[6], stby[6]), TransformFromCopy(prim[7], stby[7]),
                      VGroup(prim[6], prim[7]).animate.set_stroke(color=WHITE)], 1.0),
            (lambda: [FadeIn(prim[8], shift=0.3 * DOWN)], 0.5),
            (lambda: [TransformFromCopy(prim[8], flight)], 0.8),
            (None, 1.8),
            (lambda: [FadeIn(rd[0])], 0.5),
            (lambda: [Create(sent[0]), FadeIn(sent[1]), FadeIn(rd[1])], 0.8),
            (None, 0.6),
            (lambda: [Create(flushed[0]), FadeIn(flushed[1]), FadeIn(rd[2])], 0.8),
            (None, 0.9),
            (lambda: [Create(replayed[0]), FadeIn(replayed[1]), FadeIn(rd[3]),
                      VGroup(stby[6], stby[7]).animate.set_stroke(color=GOLD_M)], 0.8),
            (None, 0.5),
            (lambda: [GrowFromCenter(gap), FadeIn(gap_l)], 0.9),
        ])

        # ---- asynchronous commit ------------------------------------------------------------------------
        mode = chip("asynchronous", GREY_B, 24).move_to([PX - 0.3, 3.0, 0])
        ca3 = commit_arrow(9)
        ok = VGroup(tick(True, 0.18), T("OK", 26, GREEN_M)).arrange(RIGHT, buff=0.15).next_to(client, LEFT, buff=0.35)
        self.steps("By default, replication is asynchronous. A commit waits only for the primary's disk, "
                   "so the client hears OK while the record is still on its way.", [
            (lambda: [FadeOut(gap), FadeOut(gap_l), FadeIn(mode, shift=0.2 * DOWN)], 0.8),
            (None, 1.2),
            (lambda: [GrowArrow(ca3)], 0.6),
            (lambda: [FadeIn(prim[9], shift=0.3 * DOWN)], 0.6),
            (lambda: [FadeOut(ca3), FadeIn(ok, shift=0.2 * LEFT)], 0.7),
            (lambda: [flash(flight, YELLOW_M, 1.15), flash(prim[9], YELLOW_M, 1.15)], 1.0),
        ])

        # ---- crash and promote --------------------------------------------------------------------------
        dead = rlabel(PY, "primary", "crashed", RED_M)
        cross = DashedVMobject(RoundedRectangle(corner_radius=0.15, width=13.1, height=1.65, stroke_color=RED_M, stroke_width=3),
                               num_dashes=110).move_to([0, PY + 0.14, 0])
        self.steps("Then the primary crashes.", [
            (lambda: [Transform(p_lab, dead), Create(cross),
                      VGroup(*prim[:10], p_pages, p_later, p_head).animate.set_opacity(0.3), FadeOut(flight),
                      FadeOut(sent), FadeOut(flushed), FadeOut(rd)], 1.0),
        ])

        prom = rlabel(SY, "new primary", "read-write", BLUE_M)
        promote = M("SELECT pg_promote()", 22, TEAL_M).move_to([-3.2, SY - H / 2 - 0.62, 0])
        replayed7 = marker(SY, 7, "replayed", TEAL_M)
        self.steps("Postgres won't fail over by itself. You, or a tool like Patroni, promote the standby. "
                   "It replays what it has, and becomes the new primary.", [
            (None, 1.8),
            (lambda: [FadeIn(promote, shift=0.2 * UP)], 0.8),
            (None, 1.2),
            (lambda: [Transform(replayed, replayed7),
                      VGroup(stby[6], stby[7]).animate.set_stroke(color=WHITE)], 1.0),
            (lambda: [flash(s_pages, TEAL_M)], 0.7),
            (lambda: [Transform(s_lab, prom), FadeOut(mode), FadeOut(ok)], 0.9),
        ])

        lost = VGroup(prim[8], prim[9])
        lost_l = T("acknowledged, then lost", 24, RED_M).move_to([(cx(8) + cx(9)) / 2 - 0.5, 0, 0])
        self.steps("The last two payments, 63 and 31 euros, were acknowledged, but never reached the standby. Both are gone.", [
            (lambda: [lost.animate.set_opacity(1).set_stroke(color=RED_M)], 0.9),
            (lambda: [FadeIn(lost_l, shift=0.2 * UP)], 0.7),
            (None, 1.6),
            (lambda: [flash(lost, RED_M, 1.1)], 0.9),
        ])

        # ---- synchronous --------------------------------------------------------------------------------
        sync = chip("synchronous", GREEN_M, 24).move_to([PX - 0.3, 3.0, 0])
        had = VGroup(cell(SY, 8, GREEN_M), cell(SY, 9, GREEN_M))
        saved_l = T("on the standby before the OK", 24, GREEN_M).move_to(lost_l)
        self.steps("Name the standby in synchronous_standby_names, and each commit also waits until the standby has flushed "
                   "its record. Then every acknowledged payment is on the new primary.", [
            (lambda: [FadeIn(sync, shift=0.2 * DOWN)], 0.8),
            (None, 2.4),
            (lambda: [FadeOut(lost_l)], 0.4),
            (lambda: [TransformFromCopy(lost, had), lost.animate.set_stroke(color=GREEN_M), FadeOut(replayed)], 1.0),
            (lambda: [FadeIn(saved_l, shift=0.2 * UP)], 0.6),
            (None, 1.0),
            (lambda: [flash(had, GREEN_M, 1.1)], 0.9),
        ])

        wait_l = T("commits wait a round trip", 24, GOLD_M).next_to(client, LEFT, buff=0.35)
        self.steps("The price is a round trip to the standby on every commit, and if the standby goes down, commits wait.", [
            (lambda: [FadeIn(wait_l, shift=0.2 * LEFT)], 0.8),
            (None, 1.8),
            (lambda: [flash(sync, GOLD_M)], 1.0),
        ])

        self.steps("Asynchronous replication can lose the last few commits in a failover. Synchronous loses none that were acknowledged.", [
            (None, 0.8),
            (lambda: [Circumscribe(lost, color=RED_M, buff=0.08)], 1.2),
            (None, 1.2),
            (lambda: [Circumscribe(had, color=GREEN_M, buff=0.08)], 1.2),
        ])
        self.wait(0.6)
