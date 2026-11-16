from sfz import *

SAY.insert(0, (r"\bHGET\b", "H get"))
SAY.insert(0, (r"\bSMEMBERS\b", "S members"))
SAY.insert(0, (r"\bSSCAN\b", "S scan"))
SAY.insert(0, (r"\bUNLINK\b", "unlink"))
SAY.insert(0, (r"\bOBJECT ENCODING\b", "object encoding"))
SAY.insert(0, (r"\bTYPE\b", "type"))
SAY.insert(0, (r"\bHashMap\b", "hash map"))
SAY.insert(0, (r"\blistpack\b", "list pack"))
SAY.insert(0, (r"\blog N\b", "log of N"))

CMD_X, CMD_Y = -6.4, 3.2
PCX, PCY, PW, PH = 4.8, 0.85, 3.55, 3.1      # the readout panel
PLX, PVX = 3.25, 4.45
PROW = {"key": 2.0, "type": 1.45, "encoding": 0.9, "memory": 0.35, "size": -0.2}
ROWS = [1.65, 0.45, -0.75]                   # HashMap entries
FIELDS = [("status", "approved"), ("amount", "1250"), ("currency", "EUR")]
STRIP_Y = 0.45
LV = {1: -0.05, 2: 0.6, 3: 1.25}             # skip list lanes
SX = [-5.6, -4.3, -3.2, -2.1, -1.0, 0.1, 1.2, 2.3]
SCORES = [None, 5, 12, 18, 27, 40, 42, 55]
NAMES = ["head", "m-41", "m-88", "m-07", "m-52", "m-03", "m-17", "m-60"]
HEIGHT = [3, 1, 2, 1, 3, 1, 2, 1]


def fillc(color, a=0.14):
    if ManimColor(color).to_hex().upper() == "#FFFFFF":
        return BLACK
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def glow(rect, color=YELLOW_M, s=1.04):
    """Pulse a filled box's outline (Indicate would flood its fill and hide the label)."""
    return rect.animate(rate_func=there_and_back).scale(s).set_stroke(color=color, width=6)


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def right_at(m, x, y):
    return m.move_to([x - m.width / 2, y, 0])


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


def box_at(x, y, w, h, color=GREY_B, label=None, size=17, mono=True, tcolor=WHITE):
    r = RoundedRectangle(corner_radius=0.06, width=w, height=h, stroke_color=color, stroke_width=2.5)
    r.set_fill(fillc(color), 1).move_to([x, y, 0])
    if label is None:
        return VGroup(r)
    return VGroup(r, (M if mono else T)(label, size, tcolor).move_to([x, y, 0]))


def cmd(s, color=WHITE):
    return left_at(M(s, 18, color), CMD_X, CMD_Y)


def pval(row, s, color=WHITE):
    if row == "key":
        return left_at(M(s, 19, color), PLX, PROW[row])
    return left_at(T(s, 21, color), PVX, PROW[row])


def plab(row):
    return left_at(T(row, 19, GREY_B), PLX, PROW[row])


def arr(a, b, color=GREY_B, sw=2.5):
    return Arrow(a, b, buff=0, stroke_width=sw, color=color, max_tip_length_to_length_ratio=0.18, max_stroke_width_to_length_ratio=10)


class RedisEncodings(Base):
    """cache-03, section 1 (with section 4's big keys): a three-field hash, 35 bytes of data, is 215 bytes as a
    pointer-linked hash table and 77 as a listpack, which HGET scans. Past 512 fields or a 64-byte value it becomes a
    hash table. A sorted set past 128 members becomes a dict plus a skip list (1,076 bytes to 10,888, one way only).
    SMEMBERS on a million-member set holds the one thread for about 54 ms; SSCAN pages it, UNLINK frees in the background."""

    def construct(self):
        self.title_card("Redis encodings", "small keys packed in one block, big keys in real structures")

        c1 = cmd("HSET payment:43 status approved amount 1250 currency EUR")
        panel = RoundedRectangle(corner_radius=0.14, width=PW, height=PH, stroke_color=GREY_B, stroke_width=2.5)
        panel.set_fill(BLACK, 1).move_to([PCX, PCY, 0])
        pk = pval("key", "payment:43")
        labs = VGroup(*[plab(r) for r in ("type", "encoding", "memory", "size")])
        P = {"type": pval("type", "hash", BLUE_M), "encoding": pval("encoding", "?", GREY_B),
             "memory": pval("memory", "?", GREY_B), "size": pval("size", "3 fields", WHITE)}
        data = left_at(T("35 bytes of data", 22, GREEN_M), -6.3, 2.45)
        self.steps("A payment record in Redis is a hash: three fields in one key. That's 35 bytes of actual data.", [
            (lambda: [FadeIn(c1, shift=0.1 * DOWN)], 0.8),
            "in Redis is a hash",
            (lambda: [FadeIn(panel), FadeIn(pk), FadeIn(labs), *[FadeIn(v) for v in P.values()]], 0.9),
            "That's 35",
            (lambda: [FadeIn(data, shift=0.1 * DOWN)], 0.6),
        ])

        # ---- the HashMap layout --------------------------------------------------------------------------------------
        slots = VGroup(*[box_at(-5.9, y, 0.6, 0.55, GREY_B) for y in (1.65, 1.1, 0.55, 0.0)])
        slab = T("slots", 18, GREY_B).move_to([-5.9, 2.15, 0])
        ents = [box_at(-4.2, y, 1.2, 0.5, BLUE_M, "entry", 18, mono=False) for y in ROWS]
        sl_arr = [arr([-5.6, sy, 0], [-4.82, ey, 0]) for sy, ey in [(1.65, 1.65), (0.55, 0.45), (0.0, -0.75)]]
        fbox = [box_at(-2.15, y + 0.24, 1.55, 0.4, GREY_B, f, 17) for (f, _), y in zip(FIELDS, ROWS)]
        vbox = [box_at(0.5, y - 0.24, 1.7, 0.4, GREY_B, v, 17) for (_, v), y in zip(FIELDS, ROWS)]
        f_arr = [arr([-3.6, y + 0.1, 0], [-2.95, y + 0.24, 0]) for y in ROWS]
        v_arr = [arr([-3.6, y - 0.12, 0], [-0.37, y - 0.24, 0]) for y in ROWS]
        cap = T("every arrow is an 8-byte pointer, every box its own allocation", 19, GREY_B).move_to([-2.4, -1.6, 0])
        self.steps("Stored like Java's HashMap, that's slots, an entry per field, and a separate string for each field "
                   "and value, joined by 8 byte pointers.", [
            (lambda: [FadeOut(data), FadeIn(slots), FadeIn(slab)], 0.7),
            "an entry per field",
            (lambda: [*[GrowArrow(a) for a in sl_arr], *[FadeIn(e) for e in ents]], 0.8),
            "and a separate",
            (lambda: [*[GrowArrow(a) for a in f_arr + v_arr], *[FadeIn(b) for b in fbox + vbox]], 0.9),
            "joined by",
            (lambda: [*[a.animate(rate_func=there_and_back).set_color(GOLD_M) for a in sl_arr + f_arr + v_arr],
                      FadeIn(cap)], 1.0),
        ])

        self.steps("On the lab server that took 215 bytes, mostly bookkeeping.", [
            (lambda: [Transform(P["encoding"], pval("encoding", "hashtable", BLUE_M))], 0.5),
            "215",
            (lambda: [Transform(P["memory"], pval("memory", "215 bytes", RED_M))], 0.6),
            "mostly",
            (lambda: [*[glow(e[0], RED_M, 1.06) for e in ents], *[glow(s[0], RED_M, 1.06) for s in slots]], 0.9),
        ])

        # ---- the listpack ----------------------------------------------------------------------------------------------
        segs, x = [], -6.2
        lens, datas = [], []
        for f, v in FIELDS:
            for s in (f, v):
                lw = 0.36
                lc = box_at(x + lw / 2, STRIP_Y, lw, 0.6, GREY_D, str(len(s)), 15, tcolor=GREY_B)
                dw = 0.131 * len(s) + 0.22
                dc = box_at(x + lw + dw / 2, STRIP_Y, dw, 0.6, GREEN_M, s, 16)
                lens.append(lc)
                datas.append(dc)
                x += lw + dw
        strip_lab = left_at(T("one block: each entry has its length in front", 20, GREY_B), -6.2, STRIP_Y + 0.75)
        olds = [b for pair in zip(fbox, vbox) for b in pair]
        self.steps("A listpack drops the structure: the entries go one after another into one block, each with its "
                   "length in front. 77 bytes.", [
            (lambda: [FadeOut(VGroup(slots, slab, *ents, *sl_arr, *f_arr, *v_arr, cap))], 0.7),
            "the entries go",
            (lambda: [*[ReplacementTransform(o, d) for o, d in zip(olds, datas)]], 1.2),
            "each with its length",
            (lambda: [*[FadeIn(l, shift=0.1 * DOWN) for l in lens], FadeIn(strip_lab)], 0.7),
            "77 bytes",
            (lambda: [Transform(P["encoding"], pval("encoding", "listpack", GREEN_M)),
                      Transform(P["memory"], pval("memory", "77 bytes", GREEN_M))], 0.7),
        ])

        c2 = cmd("HGET payment:43 currency")
        cur = Triangle(color=GOLD_M, fill_opacity=1).scale(0.12).rotate(PI).move_to([lens[0].get_center()[0], STRIP_Y + 0.5, 0])
        self.steps("HGET walks the block from the start, skipping ahead by each length. A few short entries are quick "
                   "to scan.", [
            (lambda: [FadeOut(strip_lab), Transform(c1, c2), FadeIn(cur)], 0.7),
            (lambda: [datas[0][0].animate.set_stroke(GOLD_M)], 0.4),
            (lambda: [cur.animate.move_to([lens[2].get_center()[0], STRIP_Y + 0.5, 0]), datas[0][0].animate.set_stroke(GREEN_M)], 0.6),
            (lambda: [datas[2][0].animate.set_stroke(GOLD_M)], 0.4),
            (lambda: [cur.animate.move_to([lens[4].get_center()[0], STRIP_Y + 0.5, 0]), datas[2][0].animate.set_stroke(GREEN_M)], 0.6),
            (lambda: [datas[4][0].animate.set_stroke(TEAL_M).set_fill(fillc(TEAL_M, 0.3), 1)], 0.4),
            (lambda: [datas[5][0].animate.set_stroke(TEAL_M).set_fill(fillc(TEAL_M, 0.3), 1)], 0.5),
            "A few short",
            (lambda: [glow(VGroup(*[d[0] for d in datas]), GOLD_M, 1.0)], 0.9),
        ])

        n = ValueTracker(3)
        size = always_redraw(lambda: pval("size", f"{int(n.get_value()):,} fields", RED_M if n.get_value() > 512 else WHITE))
        dots = M("... 509 more fields ...", 18, GREY_B).move_to([-2.0, STRIP_Y - 0.75, 0])
        lim = left_at(T("limit: 512 fields, or a value over 64 bytes", 21, GOLD_M), -6.2, -1.25)
        self.steps("Walking 10,000 fields that way, on the one thread every client shares, is too slow. So past 512 "
                   "fields, or a value over 64 bytes, Redis converts the hash.", [
            (lambda: [FadeOut(cur), *[d[0].animate.set_stroke(GREEN_M).set_fill(fillc(GREEN_M), 1) for d in datas],
                      FadeOut(P["size"]), FadeIn(size)], 0.6),
            (lambda: [n.animate(rate_func=linear).set_value(512), FadeIn(dots)], 1.6),
            "So past 512",
            (lambda: [FadeIn(lim, shift=0.1 * UP)], 0.7),
            "Redis converts",
            (lambda: [n.animate.set_value(513)], 0.5),
        ])
        size.clear_updaters()

        # ---- the hash table ------------------------------------------------------------------------------------------
        BX = -1.3
        by = [1.9 - 0.42 * k for k in range(8)]
        buckets = VGroup(*[box_at(BX, y, 0.7, 0.42, BLUE_M, str(k), 15, tcolor=GREY_B) for k, y in enumerate(by)])
        inp = box_at(-5.5, by[5], 1.5, 0.5, GREY_B, "currency", 18)
        hf = box_at(-3.4, by[5], 1.3, 0.5, PURPLE_M, "hash", 20, mono=False)
        a1 = arr([-4.75, by[5], 0], [-4.05, by[5], 0])
        a2 = arr([-2.75, by[5], 0], [BX - 0.35, by[5], 0], PURPLE_M)
        out = box_at(1.15, by[5], 1.9, 0.5, TEAL_M, "currency: EUR", 17)
        a3 = arr([BX + 0.35, by[5], 0], [0.2, by[5], 0], TEAL_M)
        self.steps("Now it's a hash table: the field's hash picks its slot, so a lookup costs the same at any size. "
                   "TYPE still says hash.", [
            (lambda: [FadeOut(VGroup(*lens, *datas, dots, lim)), Transform(P["memory"], pval("memory", "larger", RED_M)),
                      Transform(P["encoding"], pval("encoding", "hashtable", BLUE_M))], 0.7),
            (lambda: [FadeIn(buckets)], 0.6),
            "the field's hash",
            (lambda: [FadeIn(inp), GrowArrow(a1), FadeIn(hf)], 0.6),
            (lambda: [GrowArrow(a2)], 0.4),
            (lambda: [GrowArrow(a3), FadeIn(out), glow(buckets[5][0], TEAL_M, 1.1)], 0.6),
            "TYPE still",
            (lambda: [P["type"].animate(rate_func=there_and_back).scale(1.25)], 0.8),
        ])

        # ---- a sorted set: dict plus skip list -------------------------------------------------------------------------
        c3 = cmd("ZADD merchants:approved 40 m-03")

        def cell(i, lv, color=GREY_B):
            lab = ("" if SCORES[i] is None else str(SCORES[i])) if lv == 1 else ""
            b = box_at(SX[i], LV[lv], 0.72, 0.46, color, lab or None, 18)
            return b

        towers = [VGroup(*[cell(i, lv) for lv in range(1, HEIGHT[i] + 1)]) for i in range(8)]
        names = VGroup(*[T(nm, 16, GREY_B).move_to([SX[i], LV[1] - 0.45, 0]) for i, nm in enumerate(NAMES)])
        links = {}
        for lv in (1, 2, 3):
            idx = [i for i in range(8) if HEIGHT[i] >= lv]
            for a, b in zip(idx, idx[1:]):
                links[(a, lv)] = arr([SX[a] + 0.37, LV[lv], 0], [SX[b] - 0.37, LV[lv], 0])
        sl_lab = left_at(T("skip list: members in score order", 20, GREY_B), -6.2, 2.0)
        dict_lab = left_at(T("dict: member to score", 20, GREY_B), -6.2, -1.25)
        dchips = VGroup(*[chip(s, TEAL_M, 18, mono=True) for s in ("m-17 → 42", "m-03 → 40", "m-88 → 12", "...")])
        dchips.arrange(RIGHT, buff=0.25)
        left_at(dchips, -6.2, -1.8)
        self.steps("A sorted set needs a member's score fast, and members in score order. Past 128 members, Redis keeps "
                   "both: a hash table from member to score, and a skip list.", [
            (lambda: [FadeOut(VGroup(buckets, inp, hf, a1, a2, a3, out)), Transform(c1, c3),
                      Transform(pk, pval("key", "merchants:approved")), Transform(P["type"], pval("type", "zset", BLUE_M)),
                      Transform(P["encoding"], pval("encoding", "listpack", GREEN_M)),
                      Transform(size, pval("size", "128 members", WHITE)),
                      Transform(P["memory"], pval("memory", "1,076 bytes", GREEN_M))], 0.9),
            "Past 128",
            (lambda: [Transform(size, pval("size", "129 members", RED_M)), Transform(P["encoding"], pval("encoding", "skiplist", BLUE_M))], 0.6),
            "a hash table from",
            (lambda: [FadeIn(dict_lab), LaggedStart(*[FadeIn(c) for c in dchips], lag_ratio=0.2)], 0.8),
            "and a skip list",
            (lambda: [FadeIn(sl_lab), LaggedStart(*[FadeIn(t) for t in towers], lag_ratio=0.08), FadeIn(names),
                      *[GrowArrow(a) for a in links.values()]], 1.0),
        ])

        hl = YELLOW_M
        self.steps("A skip list is a sorted list with express links. A search for 40 rides the top lane, and drops "
                   "down before it overshoots: about log N steps.", [
            (lambda: [*[a.animate(rate_func=there_and_back).set_color(GOLD_M) for (i, lv), a in links.items() if lv > 1]], 0.9),
            "A search for 40",
            (lambda: [towers[0][2][0].animate.set_stroke(hl, 4)], 0.4),
            (lambda: [links[(0, 3)].animate.set_color(hl), towers[4][2][0].animate.set_stroke(hl, 4)], 0.6),
            "and drops down",
            (lambda: [towers[4][1][0].animate.set_stroke(hl, 4), links[(4, 2)].animate.set_color(RED_M)], 0.6),
            (lambda: [links[(4, 2)].animate.set_color(GREY_B), towers[4][0][0].animate.set_stroke(hl, 4)], 0.5),
            (lambda: [links[(4, 1)].animate.set_color(hl), towers[5][0][0].animate.set_stroke(GREEN_M, 4).set_fill(fillc(GREEN_M, 0.3), 1)], 0.6),
            "about log N",
            (lambda: [glow(towers[5][0][0], GREEN_M, 1.15)], 0.8),
        ])

        self.steps("The switch costs memory: about one kilobyte at 128 members, nearly eleven at 129. And it never "
                   "converts back.", [
            (lambda: [Transform(size, pval("size", "128 members", WHITE)), Transform(P["memory"], pval("memory", "1,076 bytes", GREEN_M))], 0.6),
            "nearly eleven",
            (lambda: [Transform(size, pval("size", "129 members", RED_M)), Transform(P["memory"], pval("memory", "10,888 bytes", RED_M))], 0.7),
            "And it never",
            (lambda: [Transform(size, pval("size", "128 members", WHITE))], 0.6),
            (lambda: [glow(panel, BLUE_M, 1.02)], 0.8),
        ])

        # ---- big keys ----------------------------------------------------------------------------------------------------
        c4 = cmd("SMEMBERS fraud:flagged")
        TX0, TX1, TY = -5.2, 2.6, -0.2
        ms = (TX1 - TX0) / 60
        tl = Line([TX0, TY - 0.3, 0], [TX1, TY - 0.3, 0], stroke_width=2, color=GREY_B)
        tlab = left_at(T("the one thread, 60 ms", 19, GREY_B), TX0, TY + 0.55)
        small = VGroup(*[box_at(TX0 + (k * 0.7 + 0.15) * ms, TY, 0.3 * ms, 0.4, GREY_B) for k in range(3)])
        big = box_at(TX0 + 2.0 * ms + 27 * ms, TY, 54 * ms, 0.4, RED_M, "SMEMBERS: about 54 ms", 18, mono=False)
        waitlab = left_at(T("other clients waiting:", 19, GREY_B), TX0, TY - 0.95)
        q = VGroup(*[Dot(radius=0.07, color=GOLD_M) for _ in range(24)]).arrange(RIGHT, buff=0.14)
        left_at(q, waitlab.get_right()[0] + 0.25, TY - 0.95)
        self.steps("Big keys hurt in another way. A set of flagged cards grows to a million members. SMEMBERS reads it "
                   "whole, holding the only thread for about 54 milliseconds while every other client waits.", [
            (lambda: [FadeOut(VGroup(*towers, names, *links.values(), sl_lab, dict_lab, dchips))], 0.7),
            "A set of flagged",
            (lambda: [Transform(pk, pval("key", "fraud:flagged")), Transform(P["type"], pval("type", "set", BLUE_M)),
                      Transform(P["encoding"], pval("encoding", "hashtable", BLUE_M)),
                      Transform(P["memory"], pval("memory", "about 30 MB", RED_M)),
                      Transform(size, pval("size", "1,000,000 cards", RED_M))], 0.9),
            "SMEMBERS reads",
            (lambda: [Transform(c1, c4), Create(tl), FadeIn(tlab), FadeIn(small)], 0.7),
            (lambda: [GrowFromEdge(big, LEFT)], 1.4),
            "while every other",
            (lambda: [FadeIn(waitlab), LaggedStart(*[FadeIn(d, scale=0.5) for d in q], lag_ratio=0.08)], 1.2),
        ])

        pages, reds = VGroup(), []
        x = TX0 + 2.0 * ms
        for k in range(9):
            reds.append(box_at(x + 2.5 * ms, TY, 5 * ms, 0.4, RED_M))
            pages.add(reds[-1])
            pages.add(box_at(x + 5.6 * ms, TY, 0.6 * ms, 0.4, GREY_B))
            x += 6.2 * ms
        plab_ = T("SSCAN: a page at a time, other clients in between", 19, GREEN_M).move_to([(TX0 + TX1) / 2, TY + 0.55, 0])
        unl = left_at(T("UNLINK: the memory is freed on a background thread", 19, GREEN_M), TX0, TY - 1.6)
        self.steps("Read it in pages with SSCAN, so other clients get turns in between, and delete it with UNLINK, which "
                   "frees the memory on a background thread.", [
            (lambda: [Transform(c1, cmd("SSCAN fraud:flagged 0 COUNT 100")), FadeOut(tlab), FadeIn(plab_)], 0.6),
            (lambda: [ReplacementTransform(big, pages)], 1.0),
            "so other clients",
            (lambda: [LaggedStart(*[FadeOut(d, scale=0.5) for d in q], lag_ratio=0.05), FadeOut(waitlab)], 0.9),
            "and delete it",
            (lambda: [Transform(c1, cmd("UNLINK fraud:flagged")), FadeIn(unl, shift=0.1 * UP)], 0.8),
        ])

        self.steps("Small keys stay compact and get scanned. Big ones get real structures, and a command that touches "
                   "every element still blocks everyone.", [
            (lambda: [glow(panel, GREEN_M, 1.02)], 0.9),
            "Big ones",
            (lambda: [P["encoding"].animate(rate_func=there_and_back).scale(1.2)], 0.8),
            "and a command",
            (lambda: [*[glow(p[0], RED_M, 1.06) for p in reds]], 0.9),
        ])
        self.wait(0.6)
