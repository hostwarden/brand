#!/usr/bin/env python3
"""Generate every Hostwarden mark from geometry and font outlines.

    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
    .venv/bin/python src/generate.py

Writes svg/ and png/. Nothing in those folders is edited by hand:
a variant that is missing is added here.
"""

import os

import resvg_py
import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONTS = os.path.join(HERE, "fonts")

# Palette. Petrol and frost carry the mark; signal yellow is only
# ever the one lit LED, never text and never a surface.
PETROL = "#0C4A55"
DEEP = "#072E36"      # dark grounds
FROST = "#ECF2F1"     # light grounds, the tower on petrol; cool,
                      # never cream
STONE = "#A9BDBF"     # secondary text on petrol
SIGNAL = "#F9A800"    # RAL 1003 signal yellow

BOLD = os.path.join(FONTS, "BarlowSemiCondensed-Bold.ttf")
MEDIUM = os.path.join(FONTS, "BarlowSemiCondensed-Medium.ttf")

# --- The tower, on a 100 x 100 grid -------------------------------
#
# A crown of three merlons over three rack units. The crown is
# wider than the shaft and steps in, so the figure reads as a
# tower and not as a list; the units are the tower's courses.
# Its box is x 22..78, y 14..86, centred on the grid.

CROWN = "M22 14h12v9h10v-9h12v9h10v-9h12v19l-8 5H30l-8-5z"
UNITS = (41, 57, 73)          # top of each unit
UNIT_H = 13
SHAFT_X, SHAFT_W = 30, 40
LED_X, LED_BEZEL, LED_LIT = 61, 4.0, 2.4
TOWER_BOX = (22, 14, 56, 72)  # x, y, w, h


def num(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def circle(cx, cy, r):
    return (f"M{cx - r:g} {cy:g}a{r:g} {r:g} 0 1 0 {2 * r:g} 0"
            f"a{r:g} {r:g} 0 1 0 {-2 * r:g} 0z")


def tower(body, lit):
    """The tower as SVG elements; the LED bezels are holes."""
    units = "".join(
        f"M{SHAFT_X} {y}h{SHAFT_W}v{UNIT_H}h{-SHAFT_W}z"
        + circle(LED_X, y + UNIT_H / 2, LED_BEZEL)
        for y in UNITS)
    top = UNITS[0] + UNIT_H / 2
    return (f'<path fill="{body}" d="{CROWN}"/>'
            f'<path fill="{body}" fill-rule="evenodd" d="{units}"/>'
            f'<path fill="{lit}" d="{circle(LED_X, top, LED_LIT)}"/>')


# --- Type -----------------------------------------------------------


def text(font_path, s, size, x, baseline, fill, tracking=0):
    """Shaped, kerned outlines of s; returns (svg, width)."""
    data = open(font_path, "rb").read()
    hbfont = hb.Font(hb.Face(data))
    buf = hb.Buffer()
    buf.add_str(s)
    buf.guess_segment_properties()
    hb.shape(hbfont, buf, {"kern": True, "liga": True})
    tt = TTFont(font_path)
    glyphs = tt.getGlyphSet()
    order = tt.getGlyphOrder()
    scale = size / tt["head"].unitsPerEm
    pen = SVGPathPen(glyphs, ntos=num)
    cx = 0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        name = order[info.codepoint]
        glyphs[name].draw(TransformPen(
            pen, (scale, 0, 0, -scale,
                  x + (cx + pos.x_offset) * scale,
                  baseline - pos.y_offset * scale)))
        cx += pos.x_advance + tracking
    width = (cx - tracking) * scale
    return f'<path fill="{fill}" d="{pen.getCommands()}"/>', width


def x_height(font_path):
    tt = TTFont(font_path)
    return tt["OS/2"].sxHeight / tt["head"].unitsPerEm


# --- Compositions ---------------------------------------------------


def svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {w:g} {h:g}" width="{w:g}" height="{h:g}" '
            f'role="img" aria-label="{title}"><title>{title}</title>'
            f'{body}</svg>\n')


def signet(ground, body):
    tile = f'<rect width="100" height="100" fill="{ground}"/>' \
        if ground else ""
    return svg(100, 100, tile + tower(body, SIGNAL), "Hostwarden")


WORD = "hostwarden"
WORD_SIZE = 100
TRACK = 6


def wordmark(fill):
    xh = x_height(BOLD) * WORD_SIZE
    pad = 0.25 * xh
    asc = 0.75 * WORD_SIZE          # clears h, t and d
    base = pad + asc
    path, w = text(BOLD, WORD, WORD_SIZE, pad, base, fill, TRACK)
    return svg(w + 2 * pad, base + pad + 0.02 * WORD_SIZE, path,
               "hostwarden")


def lockup_parts(fill, body, h):
    """Tower at height h, word beside it. Returns (svg, w, h).

    The word stands on the tower's base line; its x-height is
    0.37 of the tower, so the crown rises clear above the ascenders.
    """
    bx, by, bw, bh = TOWER_BOX
    s = h / bh
    g = (f'<g transform="translate({-bx * s:g} {-by * s:g}) '
         f'scale({s:g})">{tower(body, SIGNAL)}</g>')
    size = 0.37 * h / x_height(BOLD)
    gap = 0.2 * h
    word, ww = text(BOLD, WORD, size, bw * s + gap, h, fill, TRACK)
    return g + word, bw * s + gap + ww, h


def lockup(fill, body):
    h = 100
    pad = 0.25 * h
    inner, w, _ = lockup_parts(fill, body, h)
    return svg(w + 2 * pad, h + 2 * pad,
               f'<g transform="translate({pad} {pad})">{inner}</g>',
               "Hostwarden")


def social():
    W, H = 1280, 640
    th = 220
    inner, lw, _ = lockup_parts(FROST, FROST, th)
    x0 = (W - lw) / 2
    y0 = 130
    tag, tw = text(MEDIUM, "System administration with safety guardrails",
                   46, 0, 0, FROST)
    sub, sw = text(MEDIUM,
                   "Linux · FreeBSD · macOS · Windows Server",
                   30, 0, 0, STONE)
    ty = y0 + th + 105
    body = (f'<rect width="{W}" height="{H}" fill="{PETROL}"/>'
            f'<g transform="translate({x0:g} {y0})">{inner}</g>'
            f'<g transform="translate({(W - tw) / 2:g} {ty})">{tag}</g>'
            f'<g transform="translate({(W - sw) / 2:g} {ty + 55})">'
            f'{sub}</g>')
    return svg(W, H, body, "Hostwarden")


# --- Output ---------------------------------------------------------

SVGS = {
    "hostwarden-signet.svg": signet(PETROL, FROST),
    "hostwarden-signet-free.svg": signet(None, PETROL),
    "hostwarden-signet-invers.svg": signet(None, FROST),
    "hostwarden-wordmark.svg": wordmark(PETROL),
    "hostwarden-wordmark-invers.svg": wordmark(FROST),
    "hostwarden-lockup.svg": lockup(PETROL, PETROL),
    "hostwarden-lockup-invers.svg": lockup(FROST, FROST),
    "hostwarden-social-preview.svg": social(),
}

PNGS = [
    # file, source, width
    ("hostwarden-avatar-1024.png", "hostwarden-signet.svg", 1024),
    ("hostwarden-avatar-512.png", "hostwarden-signet.svg", 512),
    ("favicon-16.png", "hostwarden-signet.svg", 16),
    ("favicon-32.png", "hostwarden-signet.svg", 32),
    ("favicon-48.png", "hostwarden-signet.svg", 48),
    ("apple-touch-icon-180.png", "hostwarden-signet.svg", 180),
    ("hostwarden-lockup-1200.png", "hostwarden-lockup.svg", 1200),
    ("hostwarden-lockup-invers-1200.png",
     "hostwarden-lockup-invers.svg", 1200),
    ("hostwarden-social-preview.png", "hostwarden-social-preview.svg",
     1280),
]


def main():
    for name, content in SVGS.items():
        with open(os.path.join(ROOT, "svg", name), "w") as f:
            f.write(content)
    for name, src, width in PNGS:
        png = resvg_py.svg_to_bytes(
            svg_path=os.path.join(ROOT, "svg", src), width=width)
        with open(os.path.join(ROOT, "png", name), "wb") as f:
            f.write(bytes(png))


if __name__ == "__main__":
    main()
