from sfz import *

# Kokoro says "Haddad" as "hadded"
SAY.insert(0, (r"\bHaddad\b", "Hah-dahd"))

F = 16                                       # table text size
ROW_Y = [1.45 - 0.6 * i for i in range(6)]
HDR_Y, RULE_Y, TTL_Y, Q_Y = 2.1, 1.83, 2.62, 3.22
X_L = -6.52                                  # left edge of everything
X_PID = -5.85                                # payment_id, centred
X_AMT_R = -3.35                              # amount_minor, right edge
X_EM_L = -2.95                               # customer_email, left edge
X_NM_L = 0.65                                # customer_name in the wide table, left edge
X_CEM_L, X_CNM_L = 0.95, 4.55                # the customers table's two columns, left edges
NOTE_X = 4.6                                 # centre of the notes right of the wide table
RES_Y, CHIP_Y = -2.4, -3.1

# the six export rows for Ben, Jonas and Farid (payments_export in the course database, March 2026)
ROWS = [(13, 64000, "ben.carter@example.com", "Ben Carter", "ben"),
        (16, 31500, "jonas.weber@example.com", "Jonas Weber", "jonas"),
        (17, 18999, "farid.haddad@example.com", "Farid Hadad", "farid"),
        (18, 18999, "farid.haddad@example.com", "Farid Hadad", "farid"),
        (20, 7425, "ben.carter@example.com", "Ben Carter", "ben"),
        (22, 52000, "jonas.weber@example.com", "Jonas Weber", "jonas")]
CC = {"ben": BLUE_M, "jonas": TEAL_M, "farid": GOLD_M}
CUST = {"ben": (0, "ben.carter@example.com", "Ben Carter"), "jonas": (1, "jonas.weber@example.com", "Jonas Weber"),
        "farid": (2, "farid.haddad@example.com", "Farid Haddad")}


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


def pid(i):
    return M(str(ROWS[i][0]), F).move_to([X_PID, ROW_Y[i], 0])


def amt(i):
    return right_at(M(str(ROWS[i][1]), F), X_AMT_R, ROW_Y[i])


def email(i, color=WHITE):
    return left_at(M(ROWS[i][2], F, color), X_EM_L, ROW_Y[i])


def name(i, s=None, color=WHITE):
    return left_at(M(s or ROWS[i][3], F, color), X_NM_L, ROW_Y[i])


def c_email(who, color=WHITE):
    k, e, _ = CUST[who]
    return left_at(M(e, F, color), X_CEM_L, ROW_Y[k])


def c_name(who, s=None, color=WHITE):
    k, _, n = CUST[who]
    return left_at(M(s or n, F, color), X_CNM_L, ROW_Y[k])


def hdr(s, x, align="left", color=GREY_B):
    m = M(s, F, color)
    if align == "left":
        return left_at(m, x, HDR_Y)
    if align == "right":
        return right_at(m, x, HDR_Y)
    return m.move_to([x, HDR_Y, 0])


def rule(x0, x1):
    return Line([x0, RULE_Y, 0], [x1, RULE_Y, 0], stroke_width=1.5, color=GREY_D)


def tint(x0, x1, y, color, a=0.16):
    return Rectangle(width=x1 - x0, height=0.42, stroke_width=0).set_fill(color, a).move_to([(x0 + x1) / 2, y, 0]).set_z_index(-1)


def outline(x0, x1, y, color):
    return RoundedRectangle(corner_radius=0.06, width=x1 - x0, height=0.46, stroke_color=color, stroke_width=3)\
        .move_to([(x0 + x1) / 2, y, 0])


class Normalization(Base):
    """sql-02, section 0 (with section 1's functional dependencies): payments_export repeats each customer's email and
    name on every payment. A fix to payment 18 changes one of Farid's two copies, and the table now says one email has two
    names (an update anomaly). customer_email -> customer_name is a dependency whose left side is not the key, so the email
    and name move to customers, keyed by the email; loading it refuses Farid's second spelling, and from then on one row
    holds his name for both payments."""

    def construct(self):
        self.title_card("Normalization", "store each fact once")

        ttl = left_at(T("payments_export", 22, GREY_B), X_L, TTL_Y)
        h_pid, h_amt = hdr("payment_id", X_PID, "center"), hdr("amount_minor", X_AMT_R, "right")
        h_em, h_nm = hdr("customer_email", X_EM_L), hdr("customer_name", X_NM_L)
        r_wide = rule(X_L, X_NM_L + 1.75)
        P = [pid(i) for i in range(6)]
        A = [amt(i) for i in range(6)]
        E = [email(i) for i in range(6)]
        N = [name(i) for i in range(6)]
        self.steps("A partner bank sends a file of payments every night. The quickest way to load it is one wide table, "
                   "with every detail on every row.", [
            (lambda: [FadeIn(ttl, shift=0.1 * DOWN), FadeIn(VGroup(h_pid, h_amt, h_em, h_nm)), Create(r_wide)], 0.9),
            "The quickest",
            (lambda: [LaggedStart(*[FadeIn(VGroup(P[i], A[i], E[i], N[i]), shift=0.1 * DOWN) for i in range(6)],
                                  lag_ratio=0.18)], 1.8),
        ])

        tints = [tint(X_EM_L - 0.12, X_NM_L + 1.75, ROW_Y[i], CC[ROWS[i][4]]) for i in range(6)]
        order = [0, 4, 1, 5, 2, 3]
        self.steps("Ben, Jonas and Farid paid twice each. So every email and every name is stored twice, once per payment.", [
            (lambda: [LaggedStart(*[FadeIn(tints[i]) for i in order], lag_ratio=0.25)], 1.6),
            "So every email",
            (lambda: [*[Indicate(E[i], color=CC[ROWS[i][4]], scale_factor=1.06) for i in range(6)]], 0.9),
            "and every name",
            (lambda: [*[Indicate(N[i], color=CC[ROWS[i][4]], scale_factor=1.06) for i in range(6)]], 0.9),
        ])

        q1 = left_at(M("UPDATE payments_export SET customer_name = 'Farid Haddad' WHERE payment_id = 18;", F,
                       t2c={"'Farid Haddad'": GREEN_M, "18": YELLOW_M}), X_L, Q_Y)
        cur18 = outline(X_L - 0.1, X_NM_L + 1.85, ROW_Y[3], YELLOW_M)
        res1 = left_at(M("UPDATE 1", F, GREEN_M), X_NM_L + 2.2, ROW_Y[3])
        self.steps("Farid's surname has two d's, but the file spelled it with one. "
                   "He calls support about payment 18, and the agent fixes that row.", [
            (lambda: [Indicate(N[2], color=RED_M, scale_factor=1.06), Indicate(N[3], color=RED_M, scale_factor=1.06)], 1.0),
            "He calls support",
            (lambda: [FadeIn(q1, shift=0.1 * DOWN), Create(cur18)], 0.9),
            "and the agent fixes",
            (lambda: [Transform(N[3], name(3, "Farid Haddad", GREEN_M)), FadeIn(res1, shift=0.1 * LEFT)], 0.8),
        ])

        cur17 = outline(X_L - 0.1, X_NM_L + 1.85, ROW_Y[2], RED_M)
        two = chip("one email, two names", RED_M, 20).move_to([NOTE_X + 0.2, (ROW_Y[2] + ROW_Y[3]) / 2, 0])
        self.steps("Payment 17 still has the old spelling. Now one email has two names, "
                   "and the table can't tell you which one is true.", [
            (lambda: [FadeOut(res1), Transform(N[2], name(2, "Farid Hadad", RED_M)), Transform(cur18, cur17)], 0.8),
            "Now one email",
            (lambda: [Indicate(E[2], color=GOLD_M, scale_factor=1.06), Indicate(E[3], color=GOLD_M, scale_factor=1.06)], 0.8),
            (lambda: [FadeIn(two, shift=0.1 * LEFT)], 0.6),
        ])

        anom = chip("update anomaly: some copies changed, others didn't", RED_M, 20).move_to([-2.0, CHIP_Y, 0])
        self.steps("A fact stored on many rows has to change on every one of them. "
                   "Miss one, and the table contradicts itself. That's called an update anomaly.", [
            (lambda: [FadeOut(q1), *[glow(tints[i], CC["farid"], 1.03) for i in (2, 3)]], 1.0),
            "Miss one",
            (lambda: [glow(cur18, RED_M, 1.03)], 0.9),
            "That's called",
            (lambda: [FadeIn(anom, shift=0.1 * UP)], 0.7),
        ])

        # ---- functional dependency ---------------------------------------------------------------------------------
        b_em = mbox("customer_email", GOLD_M, h=0.56, size=F).move_to([NOTE_X, 1.05, 0])
        b_nm = mbox("customer_name", GOLD_M, h=0.56, size=F).move_to([NOTE_X, -0.45, 0])
        fd = Arrow(b_em.get_bottom() + 0.06 * DOWN, b_nm.get_top() + 0.06 * UP, buff=0, stroke_width=3, color=GOLD_M,
                   max_tip_length_to_length_ratio=0.25)
        fdl = left_at(T("determines", 20, GOLD_M), NOTE_X + 0.2, 0.3)
        self.steps("Ask what the columns mean. "
                   "An email belongs to one customer, so rows with the same email should have the same name.", [
            (lambda: [FadeOut(two), FadeOut(anom), FadeOut(cur18)], 0.6),
            "An email belongs",
            (lambda: [FadeIn(b_em, shift=0.1 * DOWN)], 0.6),
            "so rows with",
            (lambda: [GrowArrow(fd), FadeIn(b_nm, shift=0.1 * DOWN), FadeIn(fdl)], 0.9),
        ])

        fdc = chip("a functional dependency", GOLD_M, 20).move_to([NOTE_X, -1.35, 0])
        key_ul = Line([X_PID - 0.67, HDR_Y - 0.2, 0], [X_PID + 0.67, HDR_Y - 0.2, 0], stroke_width=3, color=BLUE_M)
        keyc = chip("the key: names one payment", BLUE_M, 20).move_to([-4.6, RES_Y, 0])
        self.steps("That rule is a functional dependency: the email determines the name. "
                   "The payment id determines every column, because it names one payment. It's the table's key.", [
            (lambda: [FadeIn(fdc, shift=0.1 * UP), glow(b_em[0], GOLD_M, 1.05)], 0.9),
            "The payment id",
            (lambda: [Transform(h_pid, hdr("payment_id", X_PID, "center", BLUE_M)), Create(key_ul)], 0.7),
            (lambda: [*[Indicate(P[i], color=BLUE_M) for i in range(6)]], 0.8),
            "It's the table's key",
            (lambda: [FadeIn(keyc, shift=0.1 * UP)], 0.6),
        ])

        dim = VGroup(*P, *A, h_pid, h_amt, key_ul)
        self.steps("The trouble is a dependency whose left side is not the key. "
                   "Email to name is a fact about the customer, and this table stores it on every payment.", [
            (lambda: [FadeOut(keyc), dim.animate.set_opacity(0.3)], 0.8),
            "Email to name",
            (lambda: [glow(b_em[0], GOLD_M, 1.05), glow(b_nm[0], GOLD_M, 1.05)], 0.9),
            "on every payment",
            (lambda: [LaggedStart(*[glow(t, CC[ROWS[i][4]], 1.03) for i, t in enumerate(tints)], lag_ratio=0.12)], 1.1),
        ])

        # ---- split -------------------------------------------------------------------------------------------------
        ttl_c = left_at(T("customers", 22, GREY_B), X_CEM_L, TTL_Y)
        hc_em = hdr("customer_email", X_CEM_L, color=GOLD_M)
        hc_nm = hdr("customer_name", X_CNM_L)
        r_cust = rule(X_CEM_L, X_CNM_L + 1.75)
        key_c = Line([X_CEM_L, HDR_Y - 0.2, 0], [X_CEM_L + hc_em.width, HDR_Y - 0.2, 0], stroke_width=3, color=GOLD_M)
        CE = {w: c_email(w) for w in CUST}
        CN = {w: c_name(w) for w in ("ben", "jonas")}
        ttl_p = left_at(T("payments", 22, GREY_B), X_L, TTL_Y)

        def move_pair(who, rows):
            """Both copies of a customer's email and name fly into one customers row and merge."""
            an = []
            for i in rows:
                an.append(ReplacementTransform(E[i].copy(), CE[who]) if i == rows[0] else
                          Transform(E[i].copy(), CE[who].copy(), remover=True))
                an.append(ReplacementTransform(N[i], CN[who]) if i == rows[0] else
                          Transform(N[i], CN[who].copy(), remover=True))
            return an

        land = c_name("farid", "Farid Hadad")
        r_pay = rule(X_L, X_EM_L + 3.25)
        self.steps("So give that fact a table of its own. Move the email and the name into customers, "
                   "one row per email, and make the email its key.", [
            (lambda: [FadeOut(VGroup(b_em, b_nm, fd, fdl, fdc)), Transform(ttl, ttl_p)], 0.7),
            (lambda: [FadeIn(ttl_c, shift=0.1 * DOWN), FadeIn(hc_em), ReplacementTransform(h_nm, hc_nm), Create(r_cust),
                      Transform(r_wide, r_pay), *[FadeOut(t) for t in tints]], 0.8),
            "one row per email",
            (lambda: [*move_pair("ben", [0, 4]), *move_pair("jonas", [1, 5]),
                      ReplacementTransform(E[2].copy(), CE["farid"]), ReplacementTransform(N[2], land)], 1.3),
            "make the email its key",
            (lambda: [Create(key_c), *[Indicate(CE[w], color=GOLD_M, scale_factor=1.05) for w in CUST]], 0.8),
        ])

        e18 = E[3].copy()
        err = chip("ERROR: duplicate key, customer_email = farid.haddad@example.com", RED_M, 18).move_to([0, RES_Y, 0])
        cross = tick(False, 0.14).move_to([X_CEM_L - 0.38, ROW_Y[3], 0])
        self.steps("But Farid's email comes with two names. His second row has the same key, and the key refuses it. "
                   "Someone has to decide, once, which spelling is true.", [
            (lambda: [Indicate(land, color=RED_M, scale_factor=1.06), Indicate(N[3], color=GREEN_M, scale_factor=1.06)], 0.9),
            "His second row",
            (lambda: [e18.animate.move_to(left_at(M(ROWS[3][2], F), X_CEM_L, ROW_Y[3]).get_center()),
                      N[3].animate.move_to(left_at(M("Farid Haddad", F), X_CNM_L, ROW_Y[3]).get_center())], 0.9),
            "and the key refuses it",
            (lambda: [e18.animate.set_color(RED_M), N[3].animate.set_color(RED_M), Create(cross),
                      FadeIn(err, shift=0.1 * UP)], 0.7),
            "Someone has to decide",
            (lambda: [FadeOut(e18), FadeOut(N[3]), FadeOut(cross), glow(err[0], RED_M, 1.02)], 0.8),
        ])

        CN["farid"] = c_name("farid", "Farid Haddad", GREEN_M)
        self.steps("Haddad, with two d's, goes in once. The payments table keeps only the payment's own facts: "
                   "its id, its amount, and the email that points at the customer.", [
            (lambda: [FadeOut(err), ReplacementTransform(land, CN["farid"])], 0.8),
            "The payments table",
            (lambda: [dim.animate.set_opacity(1)], 0.8),
            "and the email",
            (lambda: [*[E[i].animate.set_color(CC[ROWS[i][4]]) for i in range(6)],
                      *[CE[w].animate.set_color(CC[w]) for w in CUST]], 0.9),
        ])

        links = VGroup(*[Line([X_EM_L + 3.27, ROW_Y[i], 0], [X_CEM_L - 0.1, ROW_Y[CUST["farid"][0]], 0],
                              stroke_width=2.5, color=GOLD_M) for i in (2, 3)])
        res2 = chip("UPDATE 1", GREEN_M, 20).move_to([X_CNM_L + 0.85, RES_Y + 0.75, 0])
        o_f = outline(X_CEM_L - 0.12, X_CNM_L + 1.85, ROW_Y[2], GOLD_M)
        self.steps("If Farid's name changes again, one update changes one row, "
                   "and both of his payments read it through a join.", [
            (lambda: [Transform(CN["farid"], c_name("farid", "Farid Haddad"))], 0.5),
            (lambda: [Create(o_f)], 0.6),
            "one update",
            (lambda: [FadeIn(res2, shift=0.1 * UP), glow(o_f, GOLD_M, 1.02)], 0.8),
            "and both of his payments",
            (lambda: [Create(links[0]), Create(links[1])], 0.7),
            (lambda: [Indicate(E[2], color=GOLD_M, scale_factor=1.0), Indicate(E[3], color=GOLD_M, scale_factor=1.0)], 0.8),
        ])

        self.steps("Find what determines what. Give each fact one home, keyed by what determines it, "
                   "and point at it from everywhere else.", [
            (lambda: [FadeOut(res2), Indicate(hc_em, color=GOLD_M)], 0.9),
            "keyed by",
            (lambda: [glow(o_f, GOLD_M, 1.03), Indicate(CN["farid"], color=GREEN_M)], 1.0),
            "and point at it",
            (lambda: [*[Indicate(E[i], color=CC[ROWS[i][4]], scale_factor=1.0) for i in range(6)]], 1.0),
        ])
        self.wait(0.6)
