from sfz import *

SAY.insert(0, (r"\bZADD\b", "Z add"))
SAY.insert(0, (r"\bZREM\b", "Z rem"))
SAY.insert(0, (r"\bzset\b", "Z set"))
SAY.insert(0, (r"\bskiplist\b", "skip list"))
SAY.insert(0, (r"\blistpack\b", "list pack"))
SAY.insert(0, (r"\bm-(\d+)\b", r"M \1"))
SAY.insert(0, (r"\bEUR\b", "E U R"))
SAY.insert(0, (r"\bHashMap\b", "hash map"))
SAY.insert(0, (r"\bOBJECT ENCODING\b", "object encoding"))
SAY.insert(0, (r"\bTYPE\b", "type"))

# ---- the one picture (frame about 14.2 x 8; everything stays 0.5 inside) ----
CMD_Y, STAT_Y, STRIP_Y, CAP_Y, BAR_Y = 3.05, 2.3, 0.55, -3.22, -2.72
L1, L2, L3 = -0.35, 0.5, 1.25                 # skip list lanes
HEAD_X = -5.55
NODE_X = [-3.3, -1.0, 1.3, 3.6, 5.6]
DICT_Y = -1.6


def fillc(color, a=0.14):
    return interpolate_color(ManimColor("#000000"), ManimColor(color), a)


def swap(old, new, d=UP):
    if old is None:
        return FadeIn(new, shift=0.1 * d)
    return Succession(FadeOut(old, shift=0.1 * d, run_time=0.3), FadeIn(new, shift=0.1 * d))


def left_at(m, x, y):
    return m.move_to([x + m.width / 2, y, 0])


def outline(m, color=YELLOW_M, buff=0.08):
    r = SurroundingRectangle(m, color=color, buff=buff, corner_radius=0.1, stroke_width=4).set_z_index(7)
    return Succession(Create(r, run_time=0.35), FadeOut(r, run_time=0.45))


def rbox(c, w, h, color, label=None, size=18, mono=True, tcolor=None, a=0.14):
    r = RoundedRectangle(corner_radius=0.06, width=w, height=h, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, a), 1).move_to(c)
    if label is None:
        return VGroup(r)
    t = (M if mono else T)(label, size, tcolor or WHITE).move_to(c).set_z_index(3)
    return VGroup(r, t)


def cell(label, color=WHITE, tcolor=None):
    t = M(label, 18, tcolor or color)
    w = max(0.72, t.width + 0.32)
    r = Rectangle(width=w, height=0.7, stroke_color=color, stroke_width=2.5).set_fill(fillc(color, 0.12), 1)
    t.move_to(r).set_z_index(3)
    return VGroup(r, t)


def lay(cells, y, x=0.0):
    """Positions (centres) of cells packed edge to edge, the whole row centred on x."""
    total = sum(c[0].width for c in cells)
    xs, cur = [], x - total / 2
    for c in cells:
        xs.append(np.array([cur + c[0].width / 2, y, 0]))
        cur += c[0].width
    return xs


def strip(spec, y, x=0.0):
    cells = [cell(*s) for s in spec]
    for c, p in zip(cells, lay(cells, y, x)):
        c.move_to(p)
    return cells


def link(a, b, color=GREY_B):
    return Arrow(a, b, buff=0.05, stroke_width=2.5, color=color, max_tip_length_to_length_ratio=0.18,
                 max_stroke_width_to_length_ratio=10)


class Base(VoiceScene):
    def add_mobjects_from_animations(self, animations):
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

    def cap(self, s, color=GREY_B, size=24):
        new = fit(T(s, size, color) if isinstance(s, str) else s, 13.0).move_to([0, CAP_Y, 0]).set_z_index(3)
        old, self.capm = self.capm, new
        return [swap(old, new)]

    def uncap(self):
        old, self.capm = self.capm, None
        return [FadeOut(old)] if old is not None else []

    def put(self, key, mob, d=UP):
        mob.set_z_index(3)
        old = self.lab.get(key)
        self.lab[key] = mob
        return [swap(old, mob, d)]

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


class RedisEncodings(Base):
    """cache-03, section 1. One more shop makes a sorted set eight times bigger: why? A HashMap's pointers and
    headers outweigh 35 bytes of data (215 bytes). The café owner's notebook page: a listpack, entries back to back
    with their lengths (77 bytes). The stepper's sorted set: 68 bytes, an insert that walks and moves bytes (76), 128
    members in 1,305 bytes. The page breaks at size; predict the 129th: a dict and a skip list (express lanes), 10,813
    bytes. The name: encoding (TYPE vs OBJECT ENCODING), the limits (128 and 64 bytes; 512 for hashes). The notebook
    breaks: ZREM leaves a skip list (10,741). Guardrail, moral, and a check (a hash with 600 fields)."""

    def cmd(self, s):
        return self.put("cmd", fit(M("> " + s, 18, YELLOW_M), 13.0).move_to([0, CMD_Y, 0]))

    def enc(self, s, color=TEAL_M):
        return self.put("enc", T(s, 22, color).move_to([-3.4, STAT_Y, 0]))

    def mem(self, s, color=WHITE):
        return self.put("mem", T(s, 22, color).move_to([3.4, STAT_Y, 0]))

    def construct(self):
        self.capm = None
        self.lab = {}
        self.title_card("One more shop, eight times the memory", "how Redis lays out a key")

        # ---------------- scene 1: the question ----------------
        rank = VGroup(*[rbox([0, 0, 0], 0.32, 0.32, TEAL_M) for _ in range(32)]).arrange_in_grid(4, 8, buff=0.1).move_to([0, 0.4, 0])
        extra = rbox([0, 0, 0], 0.32, 0.32, YELLOW_M).next_to(rank, RIGHT, buff=0.35).align_to(rank, DOWN)
        rlab = T("a ranked list of shops: 128 members", 22, TEAL_M).next_to(rank, DOWN, buff=0.35)
        self.steps("Redis is a program that keeps data in memory and answers requests over the network. "
                   "It keeps each piece of data under a name, called a key.", [
            "under a name",
            (lambda: [*self.put("keyname", M("merchants:approved", 22, WHITE).move_to([0, 1.75, 0]))], 0.5),
        ])
        self.steps("Here's one key: a ranked list of shops, 128 of them, in 1,305 bytes.", [
            "a ranked list",
            (lambda: [LaggedStart(*[FadeIn(b) for b in rank], lag_ratio=0.02), FadeIn(rlab)], 1.0),
            "1,305 bytes",
            (lambda: self.mem("MEMORY USAGE: 1,305 bytes"), 0.5),
        ])
        self.steps("Add one more shop. Now it takes 10,813. One more item, eight times the memory. "
                   "Where do the extra nine thousand bytes come from? Hold that question.", [
            "Add one more",
            (lambda: [FadeIn(extra, scale=0.5)], 0.4),
            "Now it takes",
            (lambda: self.mem("MEMORY USAGE: 10,813 bytes", RED_M), 0.5),
            "eight times",
            (lambda: self.cap("one more item, eight times the memory", WHITE), 0.5),
            "Hold that",
            (lambda: self.cap("where do 9,000 extra bytes come from?", YELLOW_M), 0.5),
        ], after=0.3)
        self.stamp("question")

        # ---------------- scene 2: pointers and headers ----------------
        rows_y = [1.5, 0.15, -1.2]
        slots = VGroup(*[rbox([0, 0, 0], 0.7, 0.5, GREY_B) for _ in range(4)]).arrange(DOWN, buff=0).move_to([-5.6, 0.15, 0])
        slots_t = T("slots", 19, GREY_B).next_to(slots, UP, buff=0.15)
        entries = [rbox([-3.75, y, 0], 1.15, 0.5, BLUE_M, "entry", 18, mono=False) for y in rows_y]
        fv = [("status", "approved"), ("amount", "1250"), ("currency", "EUR")]
        pieces, hdrs, arr = [], [], []
        for (f, v), y, e in zip(fv, rows_y, entries):
            for k, (s, dy) in enumerate(((f, 0.3), (v, -0.3))):
                b = rbox([-1.0, y + dy, 0], 1.75, 0.42, WHITE, s, 17)
                h = Rectangle(width=0.16, height=0.42, stroke_width=0).set_fill(GREY_C, 1).move_to(b.get_left() + [0.08, 0, 0]).set_z_index(4)
                pieces.append(b), hdrs.append(h)
                arr.append(link(e.get_right(), b.get_left() + [0.0, 0, 0], GREY_C))
        sarr = [link(slots[i].get_right(), entries[j].get_left(), GREY_C) for i, j in ((0, 0), (1, 1), (3, 2))]
        ehdr = [Rectangle(width=0.16, height=0.5, stroke_width=0).set_fill(GREY_C, 1).move_to(e.get_left() + [0.08, 0, 0]).set_z_index(4) for e in entries]
        self.steps("Start with something familiar. Java's HashMap stores three fields of a payment like this: a table of slots, "
                   "an entry for each field, and a separate piece of memory for each name and each value.", [
            (lambda: [*self.uncap(), FadeOut(rank), FadeOut(extra), FadeOut(rlab), *self.drop("keyname", "mem")], 0.6),
            "a table of slots",
            (lambda: [FadeIn(slots), FadeIn(slots_t)], 0.5),
            "an entry",
            (lambda: [*[FadeIn(e) for e in entries], *[GrowArrow(a) for a in sarr]], 0.7),
            "a separate piece",
            (lambda: [*[FadeIn(p) for p in pieces], *[GrowArrow(a) for a in arr]], 0.9),
        ])
        self.steps("Pointers join them, 8-byte addresses that say where the next piece lives. And every piece carries a small header.", [
            (lambda: [*[a.animate.set_color(YELLOW_M) for a in sarr + arr]], 0.6),
            (lambda: self.cap("pointer: an 8-byte address of the next piece", WHITE), 0.5),
            "small header",
            (lambda: [*[FadeIn(h) for h in hdrs + ehdr], *[a.animate.set_color(GREY_C) for a in sarr + arr],
                      *self.cap("every piece of memory carries a small header", WHITE)], 0.6),
        ])
        stat_x = 4.6
        d35 = T("the data: 35 bytes", 22, GREEN_M).move_to([stat_x, 0.6, 0])
        d215 = T("as a hash table: 215 bytes", 22, RED_M).move_to([stat_x, -0.2, 0])
        self.steps("The real data here, status approved, amount 1250, currency EUR, is 35 bytes. "
                   "On the lab server, the whole thing took 215. The bookkeeping weighs more than the data.", [
            "is 35 bytes",
            (lambda: [*[outline(p, GREEN_M, 0.04) for p in pieces], FadeIn(d35)], 0.8),
            "took 215",
            (lambda: [FadeIn(d215)], 0.5),
            "The bookkeeping",
            (lambda: self.cap("the bookkeeping weighs more than the data", RED_M), 0.5),
        ])
        self.steps("Multiply by ten million payments, and much of your memory holds pointers. What if we dropped the structure?", [
            "What if",
            (lambda: self.cap("wanted: drop the structure", YELLOW_M), 0.5),
        ], after=0.3)
        self.stamp("pointers")

        # ---------------- scene 3: the notebook page ----------------
        page = RoundedRectangle(corner_radius=0.08, width=2.6, height=2.3, stroke_color=GOLD_M, stroke_width=3).set_fill(fillc(GOLD_M, 0.1), 1).move_to([0, 1.1, 0])
        lines = VGroup(*[Line([-1.05, 1.85 - 0.32 * k, 0], [1.05, 1.85 - 0.32 * k, 0], stroke_width=1.5, color=GOLD_M) for k in range(6)])
        names = VGroup(*[T(n, 16, WHITE).move_to([-0.45, 1.97 - 0.32 * k, 0]) for k, n in enumerate(["Ana", "Ben", "Chen", "Dev", "Eli"])])
        finger = Dot(radius=0.09, color=YELLOW_M).move_to([0.75, 1.97, 0]).set_z_index(6)
        pg_t = T("one notebook page", 20, GOLD_M).next_to(page, LEFT, buff=0.3)
        old_pic = VGroup(slots, slots_t, *entries, *pieces, *hdrs, *ehdr, *sarr, *arr, d35, d215)
        self.steps("Picture a café owner who keeps her regulars on one notebook page. With a hundred names, the page is perfect: "
                   "one sheet, and a finger finds anyone in seconds.", [
            (lambda: [*self.uncap(), FadeOut(old_pic)], 0.6),
            "one notebook page",
            (lambda: [FadeIn(page), Create(lines), FadeIn(names), FadeIn(pg_t)], 0.8),
            "a finger finds",
            (lambda: [FadeIn(finger)], 0.2),
            (lambda: [finger.animate.move_to([0.75, 1.97 - 0.32 * 3, 0])], 0.9),
        ])
        lp = strip([("hdr", GREY_B), ("status",), ("approved",), ("amount",), ("1250",), ("currency",), ("EUR",), ("end", GREY_B)], -1.0)
        lens = [T(str(n), 13, GREY_B).move_to(c.get_corner(UL) + [0.12, 0.12, 0]) for c, n in zip(lp[1:-1], (6, 8, 6, 4, 8, 3))]
        for l in lens:
            l.set_z_index(4)
        self.steps("Redis does the same. It writes the entries one after another into one block of memory, each with its length in front, "
                   "and finds a field by reading from the start.", [
            "one after another",
            (lambda: [LaggedStart(*[FadeIn(c, shift=0.1 * RIGHT) for c in lp], lag_ratio=0.12)], 1.2),
            "its length",
            (lambda: [*[FadeIn(l) for l in lens]], 0.5),
            "reading from the start",
            (lambda: [Succession(*[outline(c, YELLOW_M, 0.03) for c in lp[1:6]])], 1.6),
        ])
        self.steps("That block is called a listpack. The same three fields take 77 bytes as a listpack, against 215 as a hash table.", [
            "a listpack",
            (lambda: [*self.enc("listpack: one block, no pointers"), *self.cap("the notebook page = one block of memory, a listpack", GOLD_M)], 0.6),
            "77 bytes",
            (lambda: self.mem("77 bytes, not 215", GREEN_M), 0.5),
        ], after=0.3)
        self.stamp("notebook")

        # ---------------- scene 4: the sorted set as a listpack ----------------
        ss = strip([("hdr", GREY_B), ("m-88",), ("12", TEAL_M), ("m-03",), ("40", TEAL_M), ("m-17",), ("42", TEAL_M), ("end", GREY_B)], STRIP_Y)
        self.steps("Now the ranked list of shops. Redis calls it a sorted set: each member has a score, and the members stay in score order.", [
            (lambda: [*self.uncap(), FadeOut(VGroup(page, lines, names, finger, pg_t, *lp, *lens)), *self.drop("enc", "mem")], 0.6),
            "a sorted set",
            (lambda: [*self.cmd("ZADD merchants:approved 42 m-17 40 m-03 12 m-88")], 0.5),
            "each member has a score",
            (lambda: [LaggedStart(*[FadeIn(c) for c in ss], lag_ratio=0.1)], 1.0),
            "score order",
            (lambda: [Succession(*[outline(ss[i], TEAL_M, 0.03) for i in (2, 4, 6)])], 1.2),
        ])
        self.steps("Three shops: a listpack of 68 bytes.", [
            (lambda: [*self.enc("OBJECT ENCODING: listpack"), *self.mem("MEMORY USAGE: 68 bytes")], 0.6),
        ])
        walker = SurroundingRectangle(ss[1], color=YELLOW_M, buff=0.04, stroke_width=4).set_z_index(7)
        new2 = [cell("m-51"), cell("41", TEAL_M)]

        def make_room():
            cells = ss[:5] + new2 + ss[5:]
            pos = lay(cells, STRIP_Y)
            for c, p in zip(new2, pos[5:7]):
                c.move_to(p)
            return [*[c.animate.move_to(p) for c, p in zip(ss[:5] + ss[5:], pos[:5] + pos[7:])]]

        self.steps("Add shop m-51 with score 41. Redis walks the block from the start until it passes 40, "
                   "then moves every byte after that point to make room.", [
            (lambda: self.cmd("ZADD merchants:approved 41 m-51"), 0.5),
            "walks the block",
            (lambda: [Create(walker)], 0.3),
            *[(lambda i=i: [walker.animate.move_to(ss[i])], 0.35) for i in (2, 3, 4)],
            "moves every byte",
            (lambda: [FadeOut(walker), *[ss[i][0].animate.set_stroke(RED_M) for i in (5, 6, 7)]], 0.4),
            (lambda: make_room(), 0.7),
            (lambda: [*[FadeIn(c, scale=0.7) for c in new2], *self.mem("MEMORY USAGE: 76 bytes")], 0.5),
            (lambda: [*[ss[i][0].animate.set_stroke(WHITE if i == 5 else (TEAL_M if i == 6 else GREY_B)) for i in (5, 6, 7)]], 0.3),
        ])
        ss = ss[:5] + new2 + ss[5:]
        self.steps("That walk sounds slow. But a short block sits side by side in memory, and the CPU streams through it fast.", [
            "side by side",
            (lambda: [Succession(*[outline(c, YELLOW_M, 0.02) for c in ss], run_time=1.4)], 1.4),
        ])
        big = strip([("hdr", GREY_B), ("m-88",), ("12", TEAL_M), ("m-03",), ("40", TEAL_M), ("... 125 more entries ...", GREY_B), ("end", GREY_B)], STRIP_Y)
        self.steps("After 124 more shops, the key holds 128 members: still one block, 1,305 bytes.", [
            "After 124",
            (lambda: [*self.cmd("ZCARD merchants:approved   (integer) 128"), FadeOut(VGroup(*ss)), *[FadeIn(c) for c in big]], 0.8),
            "1,305 bytes",
            (lambda: self.mem("MEMORY USAGE: 1,305 bytes"), 0.5),
        ], after=0.3)
        self.stamp("listpack")

        # ---------------- scene 5: the page breaks; predict the 129th ----------------
        self.steps("Where does the page break? At size. Walking ten thousand entries on every lookup, on the one thread every "
                   "client shares, is too slow. And adding in the middle means moving every byte after it.", [
            "At size",
            (lambda: self.cap("where the page breaks: size", GOLD_M), 0.5),
            "too slow",
            (lambda: self.cap("walking 10,000 entries per lookup, on the one shared thread: too slow", RED_M), 0.6),
            "moving every byte",
            (lambda: [big[5][0].animate.set_stroke(RED_M)], 0.5),
        ])
        self.steps("So at a few thousand names, the owner switches to a box of index cards and a ranked list on the wall. "
                   "Add the 129th shop. What does Redis do? Pause and guess.", [
            "a box of index cards",
            (lambda: [big[5][0].animate.set_stroke(GREY_B), *self.cap("the owner: a box of index cards, and a ranked list on the wall", GOLD_M)], 0.6),
            "Add the 129th",
            (lambda: [*self.cmd("ZADD merchants:approved 2 m-129")], 0.5),
            "Pause and guess",
            (lambda: self.cap("the 129th shop: what does Redis do?  pause and guess", YELLOW_M), 0.5),
        ], after=0)
        self.countdown(3.0)

        # skip list pieces
        head = VGroup(*[rbox([HEAD_X, y, 0], 0.55, 0.42 if y != L1 else 0.6, GREY_B) for y in (L1, L2, L3)])
        head_t = T("head", 17, GREY_B).next_to(head, DOWN, buff=0.12)
        nodes = [("m-88", "12", 1), ("m-03", "40", 2), ("m-51", "41", 1), ("m-17", "42", 3)]
        nbox, towers = [], []
        for (m, s, h), x in zip(nodes, NODE_X):
            nbox.append(rbox([x, L1, 0], 1.45, 0.6, WHITE, f"{m}  {s}", 18))
            towers.append([rbox([x, y, 0], 0.42, 0.42, TEAL_M) for y in (L2, L3)[:h - 1]])
        dots = T("...", 26, GREY_B).move_to([NODE_X[4], L1, 0])
        lane_nodes = {L1: [head[0], *nbox, dots], L2: [head[1], towers[1][0], towers[3][0]], L3: [head[2], towers[3][1]]}
        links = []
        for y, ns in lane_nodes.items():
            for a, b in zip(ns, ns[1:]):
                links.append(link([a.get_right()[0], y, 0], [b.get_left()[0], y, 0], TEAL_M if y != L1 else GREY_B))
        tail = [link([towers[3][0].get_right()[0], L2, 0], [NODE_X[4] + 0.4, L2, 0], TEAL_M),
                link([towers[3][1].get_right()[0], L3, 0], [NODE_X[4] + 0.4, L3, 0], TEAL_M)]
        sk = VGroup(head, head_t, *nbox, *[t for tw in towers for t in tw], dots, *links, *tail)
        dct = rbox([0, DICT_Y, 0], 11.4, 0.62, BLUE_M, "dict   m-17 → 42    m-03 → 40    m-51 → 41    m-88 → 12    ...", 18)

        self.steps("Inside that one ZADD, Redis copies all 129 members into two new structures, and frees the block.", [
            (lambda: [*self.uncap(), *self.enc("OBJECT ENCODING: listpack → skiplist", YELLOW_M), *self.mem("MEMORY USAGE: converting", GREY_B)], 0.6),
            "copies all 129",
            (lambda: [*[c.animate.move_to([c.get_x(), DICT_Y, 0]).set_opacity(0) for c in big]], 0.7),
            "two new structures",
            (lambda: [FadeIn(dct, shift=0.1 * UP), FadeIn(sk, lag_ratio=0.02)], 1.2),
            "frees the block",
            (lambda: [*self.cap("the block is freed", GREY_B)], 0.5),
        ])
        self.steps("A hash table maps each member to its score, like the box of cards: any shop's score in one step.", [
            "A hash table",
            (lambda: [outline(dct, BLUE_M, 0.06), *self.cap("dict, a hash table = the box of index cards", BLUE_M)], 0.8),
        ])
        self.steps("And a skip list keeps the members in score order, like the ranked list on the wall. It's a chain where some "
                   "items carry extra links that jump far ahead, like express lanes.", [
            "a skip list",
            (lambda: [*self.cap("skip list = the ranked list on the wall", TEAL_M), *[outline(b, WHITE, 0.04) for b in nbox]], 0.8),
            "extra links",
            (lambda: [*[outline(t, TEAL_M, 0.04) for tw in towers for t in tw]], 0.7),
            "express lanes",
            (lambda: [*[l.animate.set_stroke(YELLOW_M) for l in links + tail if l.get_start()[1] > L1 + 0.1]], 0.5),
            (lambda: [*[l.animate.set_stroke(TEAL_M) for l in links + tail if l.get_start()[1] > L1 + 0.1]], 0.4),
        ])
        seeker = Dot(radius=0.1, color=YELLOW_M).set_z_index(8)

        def at(x, y):
            return np.array([x, y, 0])

        self.steps("Find shop m-51, score 41. Ride the top lane: 42 is too far, so drop a lane. 40 is fine, move right. "
                   "42 again is too far, so drop again. And there it is.", [
            (lambda: [FadeIn(seeker.move_to(at(HEAD_X, L3))), *self.cap("find score 41", YELLOW_M)], 0.4),
            "42 is too far",
            (lambda: [outline(towers[3][1], RED_M, 0.05)], 0.6),
            "drop a lane",
            (lambda: [seeker.animate.move_to(at(HEAD_X, L2))], 0.4),
            "40 is fine",
            (lambda: [seeker.animate.move_to(at(NODE_X[1], L2))], 0.6),
            "42 again",
            (lambda: [outline(towers[3][0], RED_M, 0.05)], 0.6),
            "drop again",
            (lambda: [seeker.animate.move_to(at(NODE_X[1], L1 + 0.3))], 0.4),
            "there it is",
            (lambda: [seeker.animate.move_to(at(NODE_X[2], L1 + 0.3)), nbox[2][0].animate.set_stroke(GREEN_M)], 0.6),
        ])
        self.steps("Two structures, pointers everywhere, holding the same 129 members. That's where the bytes went: 10,813 of them.", [
            (lambda: [FadeOut(seeker), nbox[2][0].animate.set_stroke(WHITE)], 0.4),
            "That's where",
            (lambda: [*self.mem("MEMORY USAGE: 10,813 bytes", RED_M), *self.cap("the answer: two pointer structures, 8 times the memory", WHITE)], 0.6),
        ], after=0.3)
        self.stamp("skiplist")

        # ---------------- scene 6: the name, and the limits ----------------
        self.steps("The type didn't change. TYPE still says zset, a sorted set. What changed is the encoding, the layout behind "
                   "the type, and OBJECT ENCODING reports it.", [
            (lambda: [*self.cmd("TYPE merchants:approved   zset")], 0.5),
            "the encoding",
            (lambda: [*self.enc("OBJECT ENCODING: skiplist", TEAL_M), *self.cap("encoding: the layout behind the type", WHITE)], 0.6),
        ])
        self.steps("A sorted set switches past 128 members, or when any one member is longer than 64 bytes. A hash switches past 512 fields.", [
            "past 128",
            (lambda: self.cap(M("zset-max-listpack-entries 128    zset-max-listpack-value 64", 19, WHITE)), 0.6),
            "A hash switches",
            (lambda: self.cap(M("hash-max-listpack-entries 512    hash-max-listpack-value 64", 19, WHITE)), 0.6),
        ], after=0.3)

        # ---------------- scene 7: the notebook breaks ----------------
        self.steps("Now remove the 129th shop. Back to 128. Does it go back to a listpack?", [
            (lambda: [*self.cmd("ZREM merchants:approved m-129"), *self.uncap()], 0.5),
            "Back to 128",
            (lambda: [outline(dots, YELLOW_M, 0.08)], 0.6),
        ])
        self.steps("No. It stays a skip list, at 10,741 bytes. Here the notebook picture breaks. The owner can go back to one page "
                   "when her list shrinks. Redis keeps the card box forever, just in case.", [
            (lambda: [*self.enc("OBJECT ENCODING: skiplist (stays)", RED_M), *self.mem("MEMORY USAGE: 10,741 bytes", RED_M)], 0.6),
            "notebook picture breaks",
            (lambda: self.cap("where the notebook picture breaks: Redis converts up, never down", GOLD_M), 0.6),
        ])
        self.steps("To get the small form back, you rebuild the key.", [
            (lambda: self.cap("to shrink it again: rebuild the key", WHITE), 0.5),
        ], after=0.3)
        self.stamp("stays")

        # ---------------- scene 8: guardrail and moral ----------------
        self.steps("So if you'll have millions of a key, keep each one under the limits: few fields, short members.", [
            (lambda: self.cap("millions of keys? keep each under the limits: few fields, short members", WHITE), 0.6),
        ])
        self.steps("The moral of the story: in memory, the bookkeeping around small items often weighs more than the items. "
                   "Redis packs a small key into one block, and pays for the big structure only when the key outgrows it.", [
            (lambda: self.cap("in memory, the bookkeeping often weighs more than the items", YELLOW_M), 0.6),
            "Redis packs",
            (lambda: self.cap("small key: one block.   big key: a real structure, and its pointers", YELLOW_M), 0.6),
        ], after=0.3)

        # ---------------- scene 9: a check ----------------
        self.steps("One quick check. A payment's hash grows to 600 fields. Listpack or hash table? Pause and think.", [
            (lambda: [*self.cmd("HLEN payment:43   (integer) 600"), *self.cap("listpack or hash table?  pause and think", YELLOW_M),
                      VGroup(sk, dct).animate.set_opacity(0.2), *self.drop("enc", "mem")], 0.6),
        ], after=0)
        self.countdown(3.0)
        self.steps("Hash table. 600 is past the hash limit of 512, and it won't come back down.", [
            (lambda: [*self.uncap(), *self.enc("OBJECT ENCODING: hashtable", BLUE_M), *self.mem("600 > 512", RED_M)], 0.6),
            "won't come back",
            (lambda: self.cap("past the limit: the big encoding, for good", WHITE), 0.6),
        ], after=0.3)
        self.play(*self.cap("small keys are packed; big keys pay for pointers", YELLOW_M, 26), run_time=0.7)
        self.wait(2.0)
