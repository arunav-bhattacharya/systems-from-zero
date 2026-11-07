from sfz import *

NX = [-4.3, 0.0, 4.3]   # replica centres
NY = 0.6
CY = -2.75              # coordinator row
NAMES = "ABC"


def flow(path, color=YELLOW_M, run_time=1.0):
    """travel() that stays invisible until its turn, so it can sit anywhere inside a Succession."""
    d = Dot(radius=0.08, color=color).move_to(path.get_start()).set_opacity(0)
    line = Line(path.get_start(), path.get_end()) if isinstance(path, Arrow) else path
    return Succession(d.animate(run_time=0.05).set_opacity(1), MoveAlongPath(d, line, rate_func=smooth, run_time=run_time),
                      FadeOut(d, run_time=0.15))


def replica(i, amount, t, stroke=WHITE, text=WHITE, val=WHITE, tcol=GREY_B):
    """One replica: its name, the balance it holds and the timestamp of that write.
    Every change of state is a Transform to a freshly built replica, so the box never covers its text."""
    r = RoundedRectangle(corner_radius=0.16, width=3.3, height=2.3, stroke_color=stroke, stroke_width=3).set_fill(BLACK, 0)
    n = T(f"replica {NAMES[i]}", 30, text).move_to([-0.12, 0.65, 0])
    a = M(amount, 38, val).move_to([0, -0.05, 0])
    w = T(f"written at {t}", 24, tcol).move_to([0, -0.65, 0])
    return VGroup(r, n, a, w).move_to([NX[i], NY, 0])


class Quorums(VoiceScene):
    """nosql-06: N copies, W acknowledgements, R replies, why R + W > N overlaps, and read repair."""

    def construct(self):
        self.title_card("Quorums", "N, R and W")

        def corner(i):
            return reps[i][0].get_corner(UR) + np.array([-0.3, -0.32, 0])

        reps = VGroup(*[replica(i, "10,000", "t1") for i in range(3)])
        params = VGroup(chip("N = 3", GREY_B, 26, mono=True), chip("W = 2", GOLD_M, 26, mono=True),
                        chip("R = 1", GREEN_M, 26, mono=True), chip("R + W > N", YELLOW_M, 26, mono=True))
        params.arrange(RIGHT, buff=0.6).move_to([0, 3.2, 0])
        acct = M("A-1001 balance", 24, GREY_B).move_to([0, 2.35, 0])

        self.beat("Your store keeps three copies of every account on three nodes, so one dead machine loses nothing. "
                  "Each copy is a replica. The number of copies is called N. Here N is three.",
                  Succession(LaggedStart(*[FadeIn(r, shift=0.2 * UP) for r in reps], lag_ratio=0.25, run_time=2.0),
                             FadeIn(acct, run_time=0.6), Wait(2.2), FadeIn(params[0], shift=0.2 * DOWN, run_time=0.8)),
                  run_time=7.5)
        self.beat("Every value carries the timestamp of its write, so you can always tell which copy is newer.",
                  LaggedStart(*[Indicate(r[3], color=YELLOW_M, scale_factor=1.3) for r in reps], lag_ratio=0.2), run_time=2.2)
        self.beat("A write that waits for all three is as slow as the slowest replica, and fails while any replica is down. "
                  "So it waits for only W of them. Here W is two.",
                  Succession(Wait(4.0), FadeIn(params[1], shift=0.2 * DOWN, run_time=0.8)), run_time=6.0)

        # ---- the write, with replica C down -----------------------------------------------------------------
        down = tick(False, 0.26).move_to(corner(2))
        coord = box("coordinator", WHITE, size=28).move_to([0, CY, 0])
        ledger = box("ledger", GOLD_M, size=28).move_to([-4.6, CY, 0])
        fraud = box("fraud check", GREEN_M, size=28).move_to([-4.6, CY, 0])
        l_in = Arrow(ledger.get_right(), coord.get_left(), buff=0.15, stroke_width=3, color=GOLD_M, tip_length=0.2,
                     max_tip_length_to_length_ratio=0.5)
        f_in = Arrow(fraud.get_right(), coord.get_left(), buff=0.15, stroke_width=3, color=GREEN_M, tip_length=0.2,
                     max_tip_length_to_length_ratio=0.5)

        def to(i, col):
            return Arrow(coord.get_top(), reps[i][0].get_bottom(), buff=0.12, stroke_width=3, color=col,
                         tip_length=0.22, max_tip_length_to_length_ratio=0.5)

        w_arr = VGroup(*[to(i, GOLD_M) for i in range(3)])
        acks = VGroup(*[tick(True, 0.2).move_to(corner(i)) for i in range(2)])
        wset = VGroup(*[SurroundingRectangle(reps[i], color=GOLD_M, buff=0.1, corner_radius=0.18, stroke_width=3) for i in range(2)])
        self.beat("Replica C is down. The ledger writes a new balance, 7,000, at time t2. "
                  "The coordinator sends it to every replica. Replicas A and B store it and reply, and the ledger hears back.",
                  Succession(AnimationGroup(Transform(reps[2], replica(2, "10,000", "t1", GREY_D, GREY_D, GREY_D, GREY_D)), FadeIn(down), run_time=0.8),
                             AnimationGroup(FadeIn(coord, shift=0.2 * UP), FadeIn(ledger, shift=0.2 * RIGHT), run_time=0.8),
                             GrowArrow(l_in, run_time=0.6), flow(l_in, GOLD_M, run_time=0.8),
                             AnimationGroup(*[GrowArrow(a) for a in w_arr[:2]], Create(w_arr[2].set_opacity(0.35)), run_time=1.2),
                             AnimationGroup(*[flow(w_arr[i], GOLD_M, run_time=1.0) for i in range(2)]),
                             AnimationGroup(*[Transform(reps[i], replica(i, "7,000", "t2", val=GOLD_M, tcol=GOLD_M)) for i in range(2)], run_time=1.0),
                             AnimationGroup(FadeIn(acks, scale=0.5), Create(wset), run_time=1.0)),
                  run_time=9.0)

        self.beat("Then C comes back, still holding 10,000 from time t1. Its copy is stale, and nothing has told it.",
                  Succession(AnimationGroup(FadeOut(down), FadeOut(w_arr), FadeOut(acks), Transform(reps[2], replica(2, "10,000", "t1")), run_time=1.0),
                             Transform(reps[2], replica(2, "10,000", "t1", RED_M, val=RED_M, tcol=RED_M), run_time=1.0)),
                  run_time=3.0)

        # ---- the read ----------------------------------------------------------------------------------------
        self.beat("Now the fraud check reads the balance. The coordinator asks R replicas and keeps the newest answer.",
                  Succession(AnimationGroup(FadeOut(ledger), FadeOut(l_in), run_time=0.5),
                             FadeIn(fraud, run_time=0.5), GrowArrow(f_in, run_time=0.6),
                             AnimationGroup(FadeIn(params[2], shift=0.2 * DOWN), run_time=0.8)),
                  run_time=3.4)

        r1 = to(2, GREEN_M)
        got_old = VGroup(M("10,000", 28, RED_M), tick(False, 0.2)).arrange(RIGHT, buff=0.25).next_to(coord, RIGHT, buff=0.5)
        self.beat("With R equal to one, it might ask only C, and get the old 10,000.",
                  Succession(GrowArrow(r1, run_time=0.9), flow(r1, GREEN_M, run_time=0.8),
                             flow(Line(r1.get_end(), r1.get_start()), RED_M, run_time=0.8),
                             FadeIn(got_old, shift=0.2 * RIGHT, run_time=0.6)),
                  run_time=3.6)

        def rset(pair):
            return VGroup(*[SurroundingRectangle(reps[i], color=GREEN_M, buff=0.24, corner_radius=0.26, stroke_width=3) for i in pair])

        r2 = chip("R = 2", GREEN_M, 26, mono=True).move_to(params[2])
        rs = rset((0, 2))
        self.beat("So ask two. Two of the three replicas have the new balance, and any two replicas you pick include at least one of them.",
                  Succession(AnimationGroup(FadeOut(r1), FadeOut(got_old), Transform(params[2], r2), run_time=0.8),
                             Create(rs, run_time=0.8), Indicate(wset[0], color=YELLOW_M, scale_factor=1.05, run_time=0.8),
                             Transform(rs, rset((0, 1)), run_time=0.7),
                             AnimationGroup(Indicate(wset[0], color=YELLOW_M, scale_factor=1.05), Indicate(wset[1], color=YELLOW_M, scale_factor=1.05), run_time=0.8),
                             Transform(rs, rset((1, 2)), run_time=0.7), Indicate(wset[1], color=YELLOW_M, scale_factor=1.05, run_time=0.8)),
                  run_time=6.2)
        self.beat("Two plus two is four, more than three, so the groups always overlap. "
                  "That's the quorum rule: R plus W is greater than N.",
                  Succession(Wait(3.0), FadeIn(params[3], shift=0.2 * DOWN, run_time=0.8),
                             Indicate(params[3], color=YELLOW_M, run_time=1.0)),
                  run_time=5.6)

        r_arr = VGroup(to(1, GREEN_M), to(2, GREEN_M))
        back = [Line(a.get_end(), a.get_start()) for a in r_arr]
        got = VGroup(M("7,000", 28, GOLD_M), tick(True, 0.2)).arrange(RIGHT, buff=0.25).next_to(coord, RIGHT, buff=0.5)
        self.beat("Say it asks B and C. B's value is from t2 and C's is from t1, so the coordinator returns B's, the newer one.",
                  Succession(AnimationGroup(*[GrowArrow(a) for a in r_arr], run_time=0.9),
                             AnimationGroup(flow(back[0], GOLD_M, run_time=1.0), flow(back[1], RED_M, run_time=1.0)),
                             AnimationGroup(Indicate(reps[1][3], color=GOLD_M, scale_factor=1.3), Indicate(reps[2][3], color=RED_M, scale_factor=1.3), run_time=1.0),
                             FadeIn(got, shift=0.2 * RIGHT, run_time=0.7)),
                  run_time=5.0)

        fix = Arrow(coord.get_top(), reps[2][0].get_bottom(), buff=0.12, stroke_width=4, color=TEAL_M, tip_length=0.22,
                    max_tip_length_to_length_ratio=0.5)
        self.beat("The coordinator now knows C is behind, so it sends C the value from t2. That's read repair. Now all three copies agree.",
                  Succession(AnimationGroup(FadeOut(r_arr), FadeOut(rs), FadeOut(wset), run_time=0.6),
                             GrowArrow(fix, run_time=0.8), flow(fix, TEAL_M, run_time=1.0),
                             Transform(reps[2], replica(2, "7,000", "t2", val=GOLD_M, tcol=GOLD_M), run_time=1.0),
                             AnimationGroup(FadeOut(fix), *[Indicate(r[2], color=GOLD_M, scale_factor=1.3) for r in reps], run_time=1.2)),
                  run_time=6.0)

        self.beat("Smaller R or W answers faster and survives more failures. "
                  "Keep R plus W above N, and a read can't miss an acknowledged write.",
                  Succession(Wait(2.6), Indicate(params[3], color=YELLOW_M, scale_factor=1.15, run_time=1.4)), run_time=5.0)
        self.wait(0.6)
