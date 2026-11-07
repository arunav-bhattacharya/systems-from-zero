from sfz import *


def flash(m, color, s=1.08):
    """Indicate for solid-filled boxes: grow and recolour the outline, then back, so the label stays readable."""
    return m.animate(rate_func=there_and_back).scale(s).set_stroke(color=color)


class KafkaLog(VoiceScene):
    """kafka-01: the log, offsets, and one bookmark per reader."""

    def construct(self):
        self.title_card("The log", "Kafka's one big idea")

        W, H, X0, Y = 1.05, 0.8, -4.55, 0.4

        def cell(i, label, color=WHITE):
            c = mbox(label, color, w=W, h=H, size=20).move_to([X0 + i * (W + 0.08), Y, 0])
            n = M(str(i), 18, GREY_B).next_to(c, DOWN, buff=0.14)
            return VGroup(c, n)

        names = ["€40", "€12", "€99", "€7", "€250", "€18", "€63", "€31"]
        cells = VGroup(*[cell(i, n) for i, n in enumerate(names)])
        head = T("payments", 28, GREY_B).next_to(cells, UP, buff=0.55).align_to(cells, LEFT)

        self.beat("Kafka keeps every event in a log. A log is a list you can only add to, at the end.",
                  FadeIn(head), LaggedStart(*[FadeIn(c, shift=0.15 * RIGHT) for c in cells], lag_ratio=0.12), run_time=2.6)
        offs = VGroup(*[c[1] for c in cells])
        self.beat("Each record gets a number, its offset. Zero, one, two, and so on. A record's offset never changes.",
                  LaggedStart(*[o.animate.set_color(YELLOW_M) for o in offs], lag_ratio=0.1), run_time=2.0)
        self.play(*[o.animate.set_color(GREY_B) for o in offs], run_time=0.4)

        prod = box("producer", BLUE_M, size=26).move_to([cells[-1].get_x() + W + 0.08, 2.6, 0])
        new = cell(8, "€45", BLUE_M)
        drop = Arrow(prod.get_bottom(), new[0].get_top() + 0.05 * UP, buff=0.12, stroke_width=3, color=BLUE_M,
                     max_tip_length_to_length_ratio=0.12)
        self.beat("A producer only ever appends. The next payment lands at the end, at offset eight.",
                  FadeIn(prod), GrowArrow(drop), FadeIn(new, shift=0.3 * DOWN), run_time=2.2)
        cells.add(new)

        def reader(name, color, i, x):
            b = box(name, color, size=24).move_to([x, -2.5, 0])
            target = cells[i][1]
            a = Arrow(b.get_top(), target.get_bottom() + 0.04 * DOWN, buff=0.1, stroke_width=3, color=color,
                      max_tip_length_to_length_ratio=0.1)
            return b, a

        fraud, fa = reader("fraud check", GREEN_M, 3, -2.9)
        ledger, la = reader("ledger", GOLD_M, 7, 2.9)
        self.beat("Reading never removes anything. Each reader keeps a bookmark: the offset of the next record it will read.",
                  FadeIn(fraud), FadeIn(ledger), GrowArrow(fa), GrowArrow(la), run_time=2.4)
        self.beat("The fraud check is at offset three. The ledger is further along, at seven. They read the same log, each at its own pace.",
                  flash(cells[3][0], GREEN_M), flash(cells[7][0], GOLD_M), run_time=2.2)

        def point(b, i, color):
            return Arrow(b.get_top(), cells[i][1].get_bottom() + 0.04 * DOWN, buff=0.1, stroke_width=3, color=color,
                         max_tip_length_to_length_ratio=0.1)

        fa5 = point(fraud, 5, GREEN_M)
        self.beat("The fraud check reads two records and saves its bookmark: five.", Transform(fa, fa5), run_time=1.6)

        cross = tick(False, 0.35).next_to(fraud, RIGHT, buff=0.25)
        self.beat("Now it crashes. Nothing is lost. The records are still in the log, and the saved bookmark still says five.",
                  fraud[0].animate.set_stroke(RED_M), FadeIn(cross), run_time=1.6)
        self.beat("It restarts, reads its bookmark, and carries on from offset five. The ledger never noticed.",
                  fraud[0].animate.set_stroke(GREEN_M), FadeOut(cross), flash(cells[5][0], GREEN_M), run_time=2.0)

        seg = SurroundingRectangle(VGroup(*[cells[i] for i in range(4)]), color=RED_M, buff=0.1, corner_radius=0.1)
        seg_l = T("oldest segment, past retention", 22, RED_M).next_to(seg, UP, buff=0.12)
        self.play(FadeOut(head), run_time=0.4)
        self.beat("The log can't grow forever. After a retention period, say seven days, Kafka deletes the oldest records, a whole segment at a time.",
                  Create(seg), FadeIn(seg_l), run_time=2.4)
        self.play(FadeOut(VGroup(*[cells[i] for i in range(4)]), seg, seg_l), run_time=0.9)
        self.beat("Offsets don't shift when that happens. The log now starts at offset four, and every bookmark still means the same record.",
                  Indicate(cells[4][1], color=YELLOW_M, scale_factor=1.5), run_time=1.8)

        self.beat("That is the whole idea. Producers append at the end. Every reader keeps its own bookmark. And the log keeps records long enough for anyone to come back.",
                  VGroup(*[cells[i][0] for i in range(4, 9)]).animate(rate_func=there_and_back).scale(1.04), run_time=2.0)
        self.wait(0.6)
