from sfz import *

PX, CXR = -3.5, 3.6                                  # partition column, consumer column
PY = [2.25, 1.35, 0.45, -0.45, -1.35, -2.25]         # partitions 0..5
CYS = {1: 1.8, 2: -1.8, 3: 0.0}                      # consumers
CC = {1: GOLD_M, 2: BLUE_M, 3: GREEN_M}


def flow(path, color=YELLOW_M, run_time=1.0):
    """flow() that stays invisible until its turn, so it can sit anywhere inside a Succession."""
    d = Dot(radius=0.08, color=color).move_to(path.get_start()).set_opacity(0)
    line = Line(path.get_start(), path.get_end()) if isinstance(path, Arrow) else path
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, line, rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


class KafkaRebalance(VoiceScene):
    """kafka-07: a consumer group shares six partitions; a member joins, one crashes, partitions move."""

    def construct(self):
        self.title_card("Consumer groups", "and rebalancing")

        parts = VGroup(*[box(f"partition {i}", WHITE, w=2.2, h=0.62, size=24).move_to([PX, y, 0]) for i, y in enumerate(PY)])
        head = T("payments", 28, GREY_B).next_to(parts, UP, buff=0.3).align_to(parts, LEFT)
        peak = T("3,000 a second at peak", 24, GREY_B).next_to(head, RIGHT, buff=0.5)
        feeds = [Line([PX - 2.0, y, 0], [PX - 1.15, y, 0]) for y in PY]
        self.beat("The payments topic has six partitions, six separate logs. At peak they carry 3,000 payments a second. "
                  "One ledger consumer can book about 1,000.",
                  Succession(AnimationGroup(FadeIn(head), LaggedStart(*[FadeIn(p, shift=0.15 * RIGHT) for p in parts], lag_ratio=0.12), run_time=1.8),
                             Wait(0.6), FadeIn(peak, run_time=0.6),
                             LaggedStart(*[flow(f, YELLOW_M, run_time=0.6) for f in feeds * 2], lag_ratio=0.15, run_time=2.4)),
                  run_time=7.0)

        cons = {k: box(f"consumer {k}", CC[k], w=2.3, size=26).move_to([CXR, CYS[k], 0]) for k in (1, 2, 3)}
        grp = DashedVMobject(RoundedRectangle(corner_radius=0.2, width=2.75, height=4.9, stroke_color=GREY_B, stroke_width=2), num_dashes=60)
        grp.move_to([CXR, 0, 0])
        grp_l = T("group: ledger", 24, GREY_B).next_to(grp, UP, buff=0.18)

        def link_(i, k, col=None):
            return Arrow([PX + 1.2, PY[i], 0], cons[k].get_left() + 0.08 * LEFT, buff=0.08, stroke_width=3,
                         color=col or CC[k], tip_length=0.2, max_tip_length_to_length_ratio=0.5)

        own = {0: 1, 1: 1, 2: 1, 3: 2, 4: 2, 5: 2}
        links = {i: link_(i, own[i]) for i in range(6)}
        self.beat("So you run several consumers in one consumer group. The group splits the partitions between its members: "
                  "each partition goes to exactly one of them.",
                  Succession(AnimationGroup(Create(grp), FadeIn(grp_l), FadeIn(cons[1]), FadeIn(cons[2]), run_time=1.4),
                             Wait(1.4),
                             AnimationGroup(*[GrowArrow(links[i]) for i in range(6)],
                                            *[parts[i].animate.set_stroke(CC[own[i]]) for i in range(6)], run_time=1.6)),
                  run_time=6.0)

        def rate(k, txt, col):
            return M(txt, 22, col).next_to(cons[k], RIGHT, buff=0.6)

        rates = {k: rate(k, "1,500/s", RED_M) for k in (1, 2)}
        self.beat("With two members, each one reads three partitions, 1,500 payments a second. "
                  "That's more than it can book, so both fall behind.",
                  Succession(LaggedStart(*[flow(links[i], CC[own[i]], run_time=0.7) for i in range(6)], lag_ratio=0.12, run_time=1.6),
                             AnimationGroup(FadeIn(rates[1]), FadeIn(rates[2]), run_time=0.8),
                             Wait(1.0),
                             AnimationGroup(Indicate(rates[1], color=RED_M), Indicate(rates[2], color=RED_M), run_time=1.0)),
                  run_time=5.6)

        coord = box("group coordinator", GREY_B, size=24).move_to([0, -3.2, 0])
        self.beat("You start a third consumer. It joins the group, and the group coordinator, a broker that tracks the members, "
                  "starts a rebalance: a new split of the partitions.",
                  Succession(FadeIn(cons[3], shift=0.2 * LEFT, run_time=0.9), Wait(1.0),
                             FadeIn(coord, shift=0.2 * UP, run_time=0.8), Wait(1.6), Indicate(coord, color=WHITE, run_time=1.0)),
                  run_time=7.0)

        commit = {i: T("committed", 22, YELLOW_M).next_to(parts[i], LEFT, buff=0.25) for i in (2, 3)}
        self.beat("First it revokes two partitions. Consumer 1 gives up partition 2, and consumer 2 gives up partition 3. "
                  "Each one commits its offset, its bookmark in that partition, before letting go.",
                  Succession(AnimationGroup(Indicate(links[2], color=CC[1]), Indicate(links[3], color=CC[2]), run_time=1.2),
                             Wait(1.6),
                             AnimationGroup(FadeIn(commit[2]), FadeIn(commit[3]), run_time=0.8), Wait(1.0),
                             AnimationGroup(FadeOut(links[2]), FadeOut(links[3]), *[parts[i].animate.set_stroke(GREY_B) for i in (2, 3)],
                                            run_time=1.0)),
                  run_time=7.5)

        new = {i: link_(i, 3) for i in (2, 3)}
        self.beat("Then the coordinator assigns both to consumer 3, which starts at the committed offsets. The other four partitions never stopped.",
                  Succession(AnimationGroup(FadeOut(commit[2]), FadeOut(commit[3]), GrowArrow(new[2]), GrowArrow(new[3]),
                                            *[parts[i].animate.set_stroke(CC[3]) for i in (2, 3)], run_time=1.4),
                             Wait(1.4),
                             LaggedStart(*[flow(links[i], CC[own[i]], run_time=0.7) for i in (0, 1, 4, 5)], lag_ratio=0.2, run_time=1.6)),
                  run_time=5.6)
        links[2], links[3] = new[2], new[3]
        own.update({2: 3, 3: 3})

        rates2 = {k: rate(k, "1,000/s", GREEN_M) for k in (1, 2, 3)}
        self.beat("Now every member reads two partitions, about 1,000 payments a second, and the backlog drains.",
                  Succession(LaggedStart(*[flow(links[i], CC[own[i]], run_time=0.7) for i in range(6)], lag_ratio=0.12, run_time=1.6),
                             AnimationGroup(Transform(rates[1], rates2[1]), Transform(rates[2], rates2[2]), FadeIn(rates2[3]), run_time=1.0)),
                  run_time=3.6)
        rates[3] = rates2[3]

        crash = tick(False, 0.24).next_to(cons[3], RIGHT, buff=0.75)
        self.beat("Then consumer 3 crashes. A live consumer sends the coordinator a heartbeat every few seconds. Consumer 3's heartbeats stop.",
                  Succession(AnimationGroup(cons[3].animate.set_stroke(RED_M), FadeOut(rates[3]), FadeIn(crash), run_time=0.9),
                             Wait(1.0),
                             AnimationGroup(Indicate(cons[1], color=CC[1], scale_factor=1.08),
                                            Indicate(cons[2], color=CC[2], scale_factor=1.08), run_time=0.9),
                             Wait(0.4),
                             AnimationGroup(Indicate(cons[1], color=CC[1], scale_factor=1.08),
                                            Indicate(cons[2], color=CC[2], scale_factor=1.08), run_time=0.9)),
                  run_time=6.0)

        back = {2: link_(2, 1), 3: link_(3, 2)}
        rates3 = {k: rate(k, "1,500/s", RED_M) for k in (1, 2)}
        self.beat("After the session timeout, 45 seconds by default, the coordinator removes it "
                  "and moves partitions 2 and 3 to the survivors.",
                  Succession(Wait(1.6), Indicate(coord, color=WHITE, run_time=0.8),
                             AnimationGroup(FadeOut(cons[3]), FadeOut(crash), FadeOut(links[2]), FadeOut(links[3]), run_time=1.0),
                             AnimationGroup(GrowArrow(back[2]), GrowArrow(back[3]), parts[2].animate.set_stroke(CC[1]),
                                            parts[3].animate.set_stroke(CC[2]), run_time=1.2),
                             AnimationGroup(Transform(rates[1], rates3[1]), Transform(rates[2], rates3[2]), run_time=0.8)),
                  run_time=6.0)
        links[2], links[3] = back[2], back[3]

        again = {i: T("read again", 22, YELLOW_M).next_to(parts[i], LEFT, buff=0.25) for i in (2, 3)}
        self.beat("They start from the last committed offsets. Any payment consumer 3 read after its last commit gets read again, "
                  "so the ledger must spot duplicates.",
                  Succession(AnimationGroup(FadeIn(again[2]), FadeIn(again[3]), run_time=0.8), Wait(2.4),
                             AnimationGroup(Indicate(parts[2], color=YELLOW_M), Indicate(parts[3], color=YELLOW_M), run_time=1.2)),
                  run_time=6.0)

        d0, d1 = np.array([PX + 1.2, PY[0], 0]), cons[2].get_left() + 0.1 * LEFT
        dup = DashedLine(d0, d1, dash_length=0.12, stroke_width=3, color=RED_M)
        no = tick(False, 0.22).move_to((d0 + d1) / 2 + 0.35 * UP)
        self.beat("Why one reader per partition? If two members read the same log, both would book every payment in it. "
                  "One owner reads each payment once, in order.",
                  Succession(AnimationGroup(FadeOut(again[2]), FadeOut(again[3]), run_time=0.6),
                             Create(dup, run_time=1.0), FadeIn(no, run_time=0.5), Wait(2.2),
                             AnimationGroup(FadeOut(dup), FadeOut(no), run_time=0.6),
                             flow(links[0], CC[1], run_time=0.9)),
                  run_time=6.6)

        cap = T("6 partitions: at most 6 busy members", 26, GREY_B).move_to(coord)
        self.beat("That also caps the group. Six partitions keep at most six members busy. A seventh would sit idle.",
                  Succession(AnimationGroup(FadeOut(coord), FadeIn(cap), run_time=1.0),
                             LaggedStart(*[Indicate(p, color=WHITE, scale_factor=1.06) for p in parts], lag_ratio=0.12, run_time=1.6)),
                  run_time=4.0)
        self.wait(0.6)
