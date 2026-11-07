from sfz import *

SAY.insert(0, (r"\backs=all\b", "acks equals all"))
SAY.insert(0, (r"\bmin\.insync\.replicas\b", "min dot in sync dot replicas"))
SAY.insert(0, (r"\bin-sync\b", "in sync"))
SAY.insert(0, (r"\bNOT_ENOUGH_REPLICAS\b", "not enough replicas"))

W, H, STEP, X0 = 0.82, 0.7, 1.0, -3.0
ROWS = [1.0, -0.3, -1.6]          # broker 1 (leader), broker 2, broker 3
NAMES = ["€40", "€12", "€99", "€7", "€250", "€18", "€63", "€31"]


def cx(i):
    return X0 + i * STEP


class KafkaISR(VoiceScene):
    """kafka-03: leader and followers, the ISR, the high watermark, a slow follower, acks=all and min.insync.replicas."""

    def construct(self):
        self.title_card("Replicas and the ISR", "how Kafka decides a write is safe")

        def cell(r, i, color=WHITE):
            return mbox(NAMES[i], color, w=W, h=H, size=20).move_to([cx(i), ROWS[r], 0])

        logs = [VGroup(*[cell(r, i) for i in range(5)]) for r in range(3)]
        offs = VGroup(*[M(str(i), 18, GREY_B).move_to([cx(i), ROWS[0] - H / 2 - 0.22, 0]) for i in range(8)])
        lx = cx(0) - W / 2 - 0.3

        def rlabel(r, role, col):
            g = VGroup(T(f"broker {r + 1}", 26), T(role, 22, col)).arrange(DOWN, buff=0.1)
            return g.move_to([lx - g.width / 2, ROWS[r], 0])

        labels = [rlabel(r, "replica", GREY_B) for r in range(3)]
        self.beat("If a partition lives on one broker's disk, a dead disk loses its payments. "
                  "So Kafka keeps copies, called replicas, on three brokers.",
                  Succession(AnimationGroup(FadeIn(labels[0]), LaggedStart(*[FadeIn(c, shift=0.15 * RIGHT) for c in logs[0]], lag_ratio=0.1),
                                            FadeIn(offs[:5]), run_time=1.6),
                             Wait(1.4),
                             AnimationGroup(*[FadeIn(labels[r]) for r in (1, 2)],
                                            *[FadeIn(logs[r], shift=0.3 * DOWN) for r in (1, 2)], run_time=1.6)),
                  run_time=6.0)

        roles = [rlabel(0, "leader", BLUE_M), rlabel(1, "follower", GREY_B), rlabel(2, "follower", GREY_B)]
        prod = box("producer", BLUE_M, size=26).move_to([cx(6), 2.75, 0])
        self.beat("One replica is the leader. Producers write only to it, and only the leader gives out offsets. "
                  "The other two are followers.",
                  Succession(AnimationGroup(Transform(labels[0], roles[0]), logs[0].animate.set_stroke(BLUE_M), run_time=1.0),
                             FadeIn(prod, shift=0.2 * DOWN, run_time=0.8), Wait(1.4),
                             AnimationGroup(Transform(labels[1], roles[1]), Transform(labels[2], roles[2]), run_time=1.0)),
                  run_time=5.0)

        drop = Arrow(prod.get_bottom(), [cx(6), ROWS[0] + H / 2 + 0.05, 0], buff=0.1, stroke_width=3, color=BLUE_M,
                     max_tip_length_to_length_ratio=0.15)
        new0 = VGroup(*[cell(0, i, BLUE_M) for i in (5, 6, 7)])
        self.beat("A producer sends three payments. The leader appends them as offsets five, six and seven. For now, they exist on one disk.",
                  Succession(GrowArrow(drop, run_time=0.8),
                             LaggedStart(*[FadeIn(c, shift=0.3 * DOWN) for c in new0], lag_ratio=0.35, run_time=1.6),
                             FadeIn(offs[5:], run_time=0.5), Wait(1.6),
                             Indicate(new0, color=BLUE_M, scale_factor=1.08, run_time=1.0)),
                  run_time=6.0)
        logs[0].add(*new0)

        IL, IR = lx - 1.6, cx(7) + W / 2 + 0.4

        def isr_box(rows):
            top, bot = ROWS[rows[0]] + H / 2 + 0.25, ROWS[rows[-1]] - H / 2 - (0.45 if rows[-1] == 0 else 0.25)
            r = RoundedRectangle(corner_radius=0.16, width=IR - IL, height=top - bot, stroke_color=GREEN_M, stroke_width=3)
            return r.move_to([(IL + IR) / 2, (top + bot) / 2, 0])

        isr = isr_box([0, 1, 2])
        isr_l = T("ISR", 28, GREEN_M).next_to(isr, RIGHT, buff=0.25)
        self.beat("The followers copy the leader: each one fetches new records and appends them at the same offsets. "
                  "The leader tracks the replicas that keep up. These are its in-sync replicas, the ISR. Right now that's all three.",
                  Succession(Wait(4.2), AnimationGroup(Create(isr), FadeIn(isr_l), run_time=1.4)), run_time=7.0)

        def hw_at(k):
            x = cx(k) - STEP / 2
            ln = DashedLine([x, ROWS[0] + H / 2 + 0.12, 0], [x, ROWS[2] - H / 2 - 0.12, 0], dash_length=0.1,
                            stroke_width=3, color=YELLOW_M)
            lab = T("high watermark", 24, YELLOW_M).next_to(ln, DOWN, buff=0.3)
            return VGroup(ln, lab)

        hw = hw_at(5)
        self.beat("The high watermark marks how far every in-sync replica has copied. Here that's offset five. "
                  "Records below it are on all of them, so they're committed.",
                  Succession(AnimationGroup(Create(hw[0]), FadeIn(hw[1]), run_time=1.2), Wait(2.0),
                             AnimationGroup(*[Indicate(VGroup(*[logs[r][i] for r in range(3)]), color=YELLOW_M, scale_factor=1.04) for i in range(5)], run_time=1.4)),
                  run_time=5.6)

        cons = box("consumer", GOLD_M, size=26).move_to([cx(1), 2.75, 0])

        def read_to(k):
            return Arrow(cons.get_bottom(), [cx(k - 1), ROWS[0] + H / 2 + 0.05, 0], buff=0.1, stroke_width=3, color=GOLD_M,
                         max_tip_length_to_length_ratio=0.12)

        rd = read_to(5)
        self.beat("Consumers read only below the high watermark. They never see a payment that could vanish with the leader.",
                  Succession(FadeIn(cons, shift=0.2 * DOWN, run_time=0.8), GrowArrow(rd, run_time=0.8)), run_time=3.0)

        new1 = VGroup(*[cell(1, i) for i in (5, 6, 7)])
        stalled = rlabel(2, "disk stalled", RED_M)
        self.beat("Broker 2 fetches five to seven. Broker 3 is stuck on a stalled disk, and gets nothing. "
                  "It's still in the ISR, so the high watermark stays at five.",
                  Succession(LaggedStart(*[TransformFromCopy(new0[j], new1[j]) for j in range(3)], lag_ratio=0.3, run_time=1.6),
                             AnimationGroup(Transform(labels[2], stalled), logs[2].animate.set_stroke(RED_M), run_time=1.0),
                             Wait(2.0), Indicate(hw, color=YELLOW_M, scale_factor=1.05, run_time=1.0)),
                  run_time=7.0)
        logs[1].add(*new1)

        acks = chip("acks=all", BLUE_M, 22, mono=True).next_to(prod, RIGHT, buff=0.3)
        wait_dots = T("waiting", 22, GREY_B).next_to(prod, LEFT, buff=0.3)
        self.beat("The producer set acks=all. It hears back only when the high watermark passes its records, so one slow disk holds it up.",
                  Succession(FadeIn(acks, shift=0.2 * LEFT, run_time=0.8), Wait(1.4), FadeIn(wait_dots, run_time=0.6),
                             Indicate(labels[2], color=RED_M, run_time=1.0)),
                  run_time=5.0)

        hw8 = hw_at(8)
        ok = tick(True, 0.22).move_to(wait_dots)
        self.beat("After 30 seconds without catching up, the leader drops broker 3 from the ISR. "
                  "The high watermark jumps to eight, and the producer gets its answer.",
                  Succession(AnimationGroup(Transform(isr, isr_box([0, 1])), isr_l.animate.next_to(isr_box([0, 1]), RIGHT, buff=0.25),
                                            VGroup(labels[2], logs[2]).animate.set_opacity(0.35), FadeOut(drop), run_time=1.4),
                             Wait(1.2),
                             AnimationGroup(Transform(hw, hw8), Transform(rd, read_to(8)), run_time=1.4),
                             ReplacementTransform(wait_dots, ok, run_time=0.8)),
                  run_time=7.0)

        down2 = rlabel(1, "stopped", RED_M)
        x2 = tick(False, 0.2).move_to([cx(7) + W / 2 + 0.45, ROWS[1], 0])
        self.beat("Now broker 2 stops as well. The ISR is the leader alone, and the producer would be told a payment on one disk is safe.",
                  Succession(AnimationGroup(Transform(labels[1], down2), logs[1].animate.set_stroke(RED_M), run_time=1.0),
                             AnimationGroup(Transform(isr, isr_box([0])), isr_l.animate.next_to(isr_box([0]), RIGHT, buff=0.25),
                                            ApplyMethod(VGroup(labels[1], logs[1]).set_opacity, 0.35), FadeOut(ok), run_time=1.4)),
                  run_time=4.2)

        floor = chip("min.insync.replicas=2", GREEN_M, 22, mono=True).move_to([0, -3.25, 0])
        refuse = VGroup(tick(False, 0.2), M("NOT_ENOUGH_REPLICAS", 20, RED_M)).arrange(RIGHT, buff=0.2)
        refuse.next_to(prod, LEFT, buff=0.35)
        drop2 = Arrow(prod.get_bottom(), [cx(6), ROWS[0] + H / 2 + 0.05, 0], buff=0.1, stroke_width=3, color=RED_M,
                      max_tip_length_to_length_ratio=0.15)
        self.beat("min.insync.replicas sets a floor. At two, the leader refuses new payments with NOT_ENOUGH_REPLICAS, "
                  "and the producer keeps retrying for up to two minutes.",
                  Succession(AnimationGroup(FadeIn(floor, shift=0.2 * UP), FadeOut(cons), FadeOut(rd), run_time=1.0), Wait(1.0),
                             GrowArrow(drop2, run_time=0.7), AnimationGroup(FadeIn(refuse, shift=0.2 * LEFT), run_time=0.8),
                             FadeOut(drop2, run_time=0.5)),
                  run_time=6.0)

        self.beat("So acks=all waits for the ISR, and the floor keeps that ISR big enough. "
                  "Every acknowledged payment is on at least two disks.",
                  Succession(Wait(1.0), AnimationGroup(Indicate(isr_l, color=GREEN_M), Indicate(floor, color=GREEN_M), run_time=1.4)),
                  run_time=4.0)
        self.wait(0.6)
