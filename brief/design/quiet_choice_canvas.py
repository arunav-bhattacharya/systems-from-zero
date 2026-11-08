"""Quiet Choice: the warm-up card in three states (open, committed, night), drawn at 2x.

  videos/.venv/bin/python brief/design/quiet_choice_canvas.py <fonts dir> <out.png>
"""
import json, pathlib, sys
from PIL import Image, ImageDraw, ImageFont

FONTS, OUT = pathlib.Path(sys.argv[1]), sys.argv[2]
ROOT = pathlib.Path(__file__).resolve().parents[2]
W = json.loads((ROOT / "content/lessons/found-02.json").read_text())["warmup"]
f = lambda name, size: ImageFont.truetype(str(FONTS / name), size)
TITLE, SUB = f("InstrumentSerif-Regular.ttf", 76), f("InstrumentSans-Regular.ttf", 25)
LABEL, Q, OPT = f("InstrumentSans-Bold.ttf", 21), f("CrimsonPro-Bold.ttf", 33), f("CrimsonPro-Regular.ttf", 32)
WHY_B, WHY = f("CrimsonPro-Bold.ttf", 29), f("CrimsonPro-Regular.ttf", 29)
MONO, NOTE = f("DMMono-Regular.ttf", 21), f("DMMono-Regular.ttf", 19)

LIGHT = dict(ground="#f6f5f1", panel="#ffffff", rule="#e2e5eb", fg="#23262e", mute="#575b66", faint="#8b909b",
             tint="#eef1f5", ok="#1d7a4c", bad="#b5303a")
DARK = dict(ground="#0a0a0b", panel="#141415", rule="#2a2a2d", fg="#ececee", mute="#a6a6ad", faint="#717177",
            tint="#1d1d1f", ok="#5ccf96", bad="#f07a86")


def mix(a, b, t):
    a, b = [int(a[i:i + 2], 16) for i in (1, 3, 5)], [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def wrap(d, text, font, width):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= width:
            cur = t
        else:
            lines.append(cur); cur = w
    return lines + [cur]


CW, PAD, RING, LH, OLH = 800, 44, 15, 45, 43   # card width, padding, ring radius, question and option line heights
TX = PAD + 78                                  # option text starts after ring and letter


def card(d, x, y, P, state, measure=False):
    """Draw (or only measure) one card. state: open | committed. Returns its height."""
    inner = CW - 2 * PAD
    qlines = wrap(d, W["q"], Q, inner)
    olines = [wrap(d, o, OPT, CW - TX - PAD) for o in W["options"]]
    h = PAD + 30 + 22 + len(qlines) * LH + 26 + sum(len(l) * OLH + 18 for l in olines) - 18
    why = []
    if state == "committed":
        why = wrap(d, "Each request still needs 10 ms of work, but now it usually finds others ahead of it: 10 / 0.1 = 100 ms.", WHY, inner)
        h += 34 + 2 + 26 + LH + len(why) * 40
    h += PAD
    if measure:
        return h
    d.rounded_rectangle([x, y, x + CW, y + h], radius=30, fill=P["panel"], outline=P["rule"], width=2)
    cy = y + PAD
    d.text((x + PAD, cy), "BEFORE YOU READ  ·  GUESS, NO SCORE", font=LABEL, fill=P["faint"])
    cy += 30 + 22
    for ln in qlines:
        d.text((x + PAD, cy), ln, font=Q, fill=P["fg"]); cy += LH
    cy += 26
    rows = []
    for k, lines in enumerate(olines):
        rh = len(lines) * OLH
        right, wrong = k == W["answer"], k == 0
        if state == "open" and k == 1:      # hover: a breath of tint, nothing moves
            d.rounded_rectangle([x + PAD - 14, cy - 9, x + CW - PAD + 14, cy + rh + 1], radius=12, fill=P["tint"])
        if state == "committed" and right:
            d.rounded_rectangle([x + PAD - 14, cy - 9, x + CW - PAD + 14, cy + rh + 1], radius=12, fill=mix(P["panel"], P["ok"], .09))
        cx, ry = x + PAD + RING + 2, cy + OLH // 2 - 2  # ring centred on the first line, never on the paragraph
        if state == "open":
            d.ellipse([cx - RING, ry - RING, cx + RING, ry + RING], outline=P["mute"], width=3)
            tc, lc = P["fg"], P["faint"]
        else:
            col = P["ok"] if right else P["bad"] if wrong else mix(P["panel"], P["faint"], .7)
            d.ellipse([cx - RING, ry - RING, cx + RING, ry + RING], outline=col, width=3)
            if right or wrong:
                d.ellipse([cx - 7, ry - 7, cx + 7, ry + 7], fill=col)
            tc = P["fg"] if right or wrong else mix(P["panel"], P["fg"], .45)
            lc = col if right or wrong else mix(P["panel"], P["faint"], .6)
        d.text((x + PAD + 46, cy + 10), "ABCD"[k], font=MONO, fill=lc)
        for i, ln in enumerate(lines):
            d.text((x + TX, cy + i * OLH), ln, font=OPT, fill=tc)
        rows.append((cx, ry))
        cy += rh + 18
    if state == "committed":
        cy += 34 - 18
        d.line([x + PAD, cy, x + CW - PAD, cy], fill=P["rule"], width=2)
        cy += 26
        d.text((x + PAD, cy), "Not quite. The answer is C.", font=WHY_B, fill=P["fg"]); cy += LH
        for ln in why:
            d.text((x + PAD, cy), ln, font=WHY, fill=P["mute"]); cy += 40
    return h, rows


def main():
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    M, GAP, TOP = 120, 80, 300
    h_open, h_com = card(probe, 0, 0, LIGHT, "open", True), card(probe, 0, 0, LIGHT, "committed", True)
    H = TOP + max(h_open, h_com) + 300
    Wd = 2 * M + 3 * CW + 2 * GAP
    img = Image.new("RGB", (Wd, H), LIGHT["ground"])
    d = ImageDraw.Draw(img)
    d.text((M, 96), "Quiet Choice", font=TITLE, fill=LIGHT["fg"])
    d.text((M + 2, 196), "one ring per answer  ·  the card is the only frame  ·  colour only after the choice", font=SUB, fill=LIGHT["mute"])
    xs = [M + i * (CW + GAP) for i in range(3)]
    # the night state sits on its own ground, with the same soft corners as the cards
    d.rounded_rectangle([xs[2] - 40, TOP - 40, xs[2] + CW + 40, TOP + h_com + 40], radius=44, fill=DARK["ground"])
    _, rows = card(d, xs[0], TOP, LIGHT, "open")
    card(d, xs[1], TOP, LIGHT, "committed")
    card(d, xs[2], TOP, DARK, "committed")
    # numbered markers in the margin left of the first card, and the legend under it
    for n, (cx, ry) in zip("12", [rows[0], rows[1]]):
        mx = xs[0] - 46
        d.ellipse([mx - 14, ry - 14, mx + 14, ry + 14], outline=LIGHT["faint"], width=2)
        d.text((mx, ry), n, font=NOTE, fill=LIGHT["mute"], anchor="mm")
        d.line([mx + 18, ry, xs[0] - 8, ry], fill=LIGHT["rule"], width=2)
    base = TOP + max(h_open, h_com) + 70
    notes = [
        ["open", "1  ring 16 px, stroke 1.5, centred on the first line", "2  hover: a breath of tint, no outline, nothing moves", "   letters in faint mono, for reference only"],
        ["committed", "the right answer fills green, a wrong pick fills red", "every other answer steps back to grey", "one hairline, then the reason"],
        ["night", "the same weights, recalibrated for a dark ground", "signal colours lifted, never inverted", ""],
    ]
    for x, ns in zip(xs, notes):
        d.text((x, base), ns[0].upper(), font=LABEL, fill=LIGHT["fg"])
        for i, t in enumerate(ns[1:]):
            d.text((x, base + 44 + i * 34), t, font=NOTE, fill=LIGHT["mute"])
    img.save(OUT, optimize=True)
    print(OUT, img.size)


main()
