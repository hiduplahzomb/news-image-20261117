#!/usr/bin/env python3
"""Entry for make.fun news-image-20261117: sum up the world news of
Tuesday 17 November 2026 in one 1024x1024 image.

Draws a newspaper front page with the standard library only: the layout,
text (DejaVu Sans glyphs from font.bin) and icons are all rendered here
in code. Deterministic: every run writes identical bytes.
Run:  mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import draw  # noqa: E402

W, H = 1024, 1024
MARGIN = 36
CW = W - 2 * MARGIN  # content width: 952

PAPER = (247, 243, 235)
INK = (26, 26, 26)
RED = (180, 35, 24)
MUTED = (107, 103, 94)
RULE = (208, 201, 184)
NAVY = (23, 37, 84)
WHITE = (255, 255, 255)

BLUE = (29, 78, 216)     # Europe
AMBER = (180, 83, 9)     # Middle East
TEAL = (15, 118, 110)    # Asia / diplomacy
SKY = (3, 105, 161)      # Asia / security
PURPLE = (147, 51, 234)  # Asia / politics

DATE_LINE = "TUESDAY \u2022 17 NOVEMBER 2026"

LEAD = {
    "kicker": "EUROPE \u2022 CONFLICT",
    "color": BLUE,
    "headline": "UKRAINE STRIKES KERCH BRIDGE AGAIN",
    "text": ("A road span falls into the strait on a second day of "
             "strikes; Russia hits Kyiv\u2019s bridges."),
}

STORIES = [
    {
        "kicker": "MIDDLE EAST \u2022 SECURITY",
        "color": AMBER,
        "icon": "drone",
        "headline": "IRAN DRONES TARGET U.S. BASE IN BAHRAIN",
        "text": ("Bahrain shoots down the drones; mines strike "
                 "tankers near Hormuz."),
    },
    {
        "kicker": "ASIA \u2022 DIPLOMACY",
        "color": TEAL,
        "icon": "globe",
        "headline": "TRUMP OPENS ASIA TRIP AT QUAD SUMMIT",
        "text": ("Leaders meet in Manila; Xi, Trump and Putin to "
                 "meet in Shenzhen."),
    },
    {
        "kicker": "ASIA \u2022 SECURITY",
        "color": SKY,
        "icon": "jet",
        "headline": "JAPAN SCRAMBLES JETS ON RUSSIAN INCURSION",
        "text": ("Two suspected Russian planes enter Japanese "
                 "airspace; Tokyo protests."),
    },
    {
        "kicker": "ASIA \u2022 POLITICS",
        "color": PURPLE,
        "icon": "document",
        "headline": "MONGOLIAN PRESIDENT RESIGNS",
        "text": ("Ukhnaagiin Kh\u00fcrels\u00fckh steps down as a "
                 "corruption scandal grows."),
    },
]

ALSO = [
    "Depardieu admits sexual assault charge in a Paris court",
    "COP31 climate talks split over fossil fuels and finance",
    "Pentagon fails its audit for the ninth straight year",
]

FOOTER = ("Every story happened, or was first reported, on "
          "Tuesday 17 November 2026.")


# ---------------------------------------------------------------- icons ----

def icon_drone(c, x, y, s, color):
    c.rounded_rect(x, y, s, s, 10, color)
    cx, cy = x + s // 2, y + s // 2
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        c.line(cx, cy, cx + dx * 15, cy + dy * 15, WHITE, 3)
        c.circle(cx + dx * 16, cy + dy * 16, 5, WHITE)
    c.rounded_rect(cx - 8, cy - 5, 16, 10, 3, WHITE)


def icon_globe(c, x, y, s, color):
    c.rounded_rect(x, y, s, s, 10, color)
    cx, cy = x + s // 2, y + s // 2
    c.ring(cx, cy, 18, 3, WHITE)
    c.ellipse_outline(cx, cy, 8, 18, WHITE, 2)
    c.ellipse_outline(cx, cy, 18, 8, WHITE, 2)


def icon_jet(c, x, y, s, color):
    c.rounded_rect(x, y, s, s, 10, color)
    pts = [(x + 48, y + 28), (x + 18, y + 13), (x + 25, y + 25),
           (x + 12, y + 21), (x + 12, y + 35), (x + 25, y + 31),
           (x + 18, y + 43)]
    c.polygon(pts, WHITE)


def icon_document(c, x, y, s, color):
    c.rounded_rect(x, y, s, s, 10, color)
    c.rounded_rect(x + 19, y + 12, 18, 32, 2, WHITE)
    c.polygon([(x + 30, y + 12), (x + 37, y + 12), (x + 37, y + 19)],
              color)
    for yy in (y + 21, y + 27, y + 33):
        c.rect(x + 23, yy, 10, 2, color)
    c.circle(x + 35, y + 38, 5, RED)
    c.circle(x + 35, y + 38, 2, WHITE)


ICONS = {"drone": icon_drone, "globe": icon_globe, "jet": icon_jet,
         "document": icon_document}


def draw_bridge(c, x, y, w, h):
    """A bridge with a broken span and an explosion, on a navy panel."""
    c.rounded_rect(x, y, w, h, 10, NAVY)
    deck_y = y + 96
    # Water lines.
    for i, yy in enumerate((y + 118, y + 126, y + 134)):
        c.line(x + 18 + i * 12, yy, x + w - 18 - i * 8, yy,
               (120, 150, 200), 2)
    # Towers.
    c.rect(x + 52, y + 34, 8, deck_y - (y + 34), WHITE)
    c.rect(x + 212, y + 34, 8, deck_y - (y + 34), WHITE)
    # Main cables.
    c.line(x + 56, y + 34, x + 134, y + 70, WHITE, 2)
    c.line(x + 134, y + 70, x + 216, y + 34, WHITE, 2)
    c.line(x + 56, y + 34, x + 12, deck_y, WHITE, 2)
    c.line(x + 216, y + 34, x + 276, deck_y, WHITE, 2)
    # Suspenders on the intact spans.
    for sx, sy in ((80, 45), (105, 57), (130, 68), (230, 47), (250, 65)):
        c.line(x + sx, y + sy, x + sx, deck_y, WHITE, 1)
    # Deck, broken between x+140 and x+196.
    c.rect(x + 12, deck_y, 128, 6, WHITE)
    c.rect(x + 196, deck_y, 80, 6, WHITE)
    # Dangling broken ends.
    c.line(x + 140, deck_y + 3, x + 150, deck_y + 13, WHITE, 4)
    c.line(x + 196, deck_y + 3, x + 186, deck_y + 13, WHITE, 4)
    # Explosion at the gap.
    ex, ey = x + 168, deck_y - 2
    for dx, dy in ((0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1),
                   (-1, 0), (-1, -1)):
        c.line(ex, ey, ex + dx * 17, ey + dy * 17, (250, 204, 21), 3)
    c.circle(ex, ey, 11, (250, 204, 21))
    c.circle(ex, ey, 6, (234, 88, 12))
    # Smoke.
    for sx, sy, sr in ((-18, -32, 8), (0, -44, 10), (18, -32, 8)):
        c.circle(ex + sx, ey + sy, sr, (168, 168, 168))


# --------------------------------------------------------------- layout ----

def fit_lines(font, text, size, width, max_lines, bold=False,
              min_size=18):
    """Largest size <= `size` at which text wraps to <= max_lines."""
    while size > min_size:
        if len(font.wrap(text, size, width, bold)) <= max_lines:
            return size
        size -= 1
    return size


def fit_size(font, text, start, width, bold=True):
    """Largest size <= start at which text fits in width."""
    size = start
    while size > 10 and font.measure(text, size, bold) > width:
        size -= 2
    return size


def masthead(c, font):
    c.rect(MARGIN, 34, CW, 3, INK)
    c.text_centered(font, W // 2, 104, "THE WORLD TODAY", 62, INK, True)
    c.text_centered(font, W // 2, 150, DATE_LINE, 34, RED, True)
    c.rect(MARGIN, 166, CW, 2, INK)
    c.rect(MARGIN, 172, CW, 1, INK)


def lead(c, font):
    y = 188
    c.text(font, MARGIN, y + 22, LEAD["kicker"], 20, LEAD["color"], True)
    size = fit_size(font, LEAD["headline"], 48, CW)
    c.text(font, MARGIN, y + 78, LEAD["headline"], size, INK, True)
    dsize = fit_lines(font, LEAD["text"], 27, 640, 2)
    lines = font.wrap(LEAD["text"], dsize, 640)
    ly = y + 116
    for line in lines[:2]:
        c.text(font, MARGIN, ly, line, dsize, INK)
        ly += dsize + 7
    draw_bridge(c, 700, y + 92, 288, 144)


def grid_cell(c, font, x, y, story):
    ICONS[story["icon"]](c, x, y, 56, story["color"])
    c.text(font, x + 68, y + 35, story["kicker"], 19, story["color"],
           True)
    hsize = fit_lines(font, story["headline"], 30, 464, 2, bold=True)
    lines = font.wrap(story["headline"], hsize, 464, bold=True)
    ly = y + 90
    for line in lines[:2]:
        c.text(font, x, ly, line, hsize, INK, True)
        ly += hsize + 7
    dsize = fit_lines(font, story["text"], 23, 464, 2)
    lines = font.wrap(story["text"], dsize, 464)
    ly = y + 154
    for line in lines[:2]:
        c.text(font, x, ly, line, dsize, INK)
        ly += dsize + 6


def grid(c, font):
    positions = [(MARGIN, 464), (MARGIN + 488, 464),
                 (MARGIN, 660), (MARGIN + 488, 660)]
    for story, (x, y) in zip(STORIES, positions):
        grid_cell(c, font, x, y, story)


def also_strip(c, font):
    c.rect(MARGIN, 858, CW, 1, RULE)
    c.text(font, MARGIN, 890, "ALSO TODAY", 20, RED, True)
    ly = 922
    for item in ALSO:
        c.text(font, MARGIN, ly, "\u2022", 24, RED, True)
        c.text(font, MARGIN + 26, ly, item, 24, INK)
        ly += 30
    c.text_centered(font, W // 2, 1010, FOOTER, 19, MUTED)


def build():
    font = draw.Font(draw.font_path())
    c = draw.Canvas(W, H, PAPER)
    masthead(c, font)
    lead(c, font)
    c.rect(MARGIN, 448, CW, 1, RULE)
    grid(c, font)
    also_strip(c, font)
    return c


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    size = draw.write_png(path, build())
    print(f"wrote {path} ({size} bytes)")


if __name__ == "__main__":
    main()
