#!/usr/bin/env python3
"""
make.fun bounty news-image-20261125
Renders a 1024x1024 PNG summarizing world news of 25 November 2026.

Standard library only: zlib (deflate compression for the PNG IDAT stream)
and struct (big-endian chunk framing + CRC32 packing). No network access,
no third-party packages, no image library. The PNG encoder, the bitmap
font and all drawing primitives (rects/circles/triangles/lines) below are
written from scratch.
"""

import os
import struct
import zlib

WIDTH = 1024
HEIGHT = 1024

BG = (8, 12, 28)          # dark navy background
CARD_BG = (18, 25, 54)    # slightly lighter navy for cards
TITLE_BAR = (14, 19, 44)
WHITE = (235, 240, 250)
DIM = (150, 165, 195)

# ---------------------------------------------------------------------------
# 5x7 bitmap font. Each glyph is 7 rows x 5 columns of '1'/'0'. Supports
# A-Z, 0-9, space and punctuation: . , ' - : $ % /
# ---------------------------------------------------------------------------
FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01111", "10000", "10000", "10011", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10101", "10011", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    ",": ["00000", "00000", "00000", "00000", "00000", "01100", "01000"],
    "'": ["01000", "01000", "00000", "00000", "00000", "00000", "00000"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    ":": ["00000", "01100", "01100", "00000", "01100", "01100", "00000"],
    "$": ["00100", "01111", "10100", "01110", "00101", "11110", "00100"],
    "%": ["11001", "11010", "00010", "00100", "01000", "01011", "10011"],
    "/": ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
}

GLYPH_W = 5
GLYPH_H = 7
CHAR_ADVANCE = 6  # 5px glyph + 1px spacing, scaled by `scale`


def char_width(scale):
    return CHAR_ADVANCE * scale


def text_width(text, scale):
    return len(text) * char_width(scale)


def max_chars_for_width(width_px, scale):
    return width_px // char_width(scale)


# ---------------------------------------------------------------------------
# Pixel buffer + drawing primitives
# ---------------------------------------------------------------------------
class Image:
    def __init__(self, width, height, bg):
        self.width = width
        self.height = height
        row = bytearray(bytes(bg) * width)
        self.rows = [bytearray(row) for _ in range(height)]

    def set_pixel(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            i = x * 3
            self.rows[y][i:i + 3] = bytes(color)

    def fill_rect(self, x0, y0, w, h, color):
        xs = max(0, x0)
        xe = min(self.width, x0 + w)
        if xe <= xs:
            return
        ys = max(0, y0)
        ye = min(self.height, y0 + h)
        chunk = bytes(color) * (xe - xs)
        for y in range(ys, ye):
            self.rows[y][xs * 3:xe * 3] = chunk

    def fill_circle(self, cx, cy, r, color):
        for y in range(cy - r, cy + r + 1):
            dy = y - cy
            rem = r * r - dy * dy
            if rem < 0:
                continue
            dx = int(rem ** 0.5)
            self.fill_rect(cx - dx, y, 2 * dx + 1, 1, color)

    def fill_triangle(self, p1, p2, p3, color):
        xs = [p1[0], p2[0], p3[0]]
        ys = [p1[1], p2[1], p3[1]]
        x0, x1 = max(min(xs), 0), min(max(xs), self.width - 1)
        y0, y1 = max(min(ys), 0), min(max(ys), self.height - 1)

        def sign(a, b, c):
            return (a[0] - c[0]) * (b[1] - c[1]) - (b[0] - c[0]) * (a[1] - c[1])

        for y in range(y0, y1 + 1):
            row = self.rows[y]
            for x in range(x0, x1 + 1):
                pt = (x, y)
                d1 = sign(pt, p1, p2)
                d2 = sign(pt, p2, p3)
                d3 = sign(pt, p3, p1)
                has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
                has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
                if not (has_neg and has_pos):
                    i = x * 3
                    row[i:i + 3] = bytes(color)

    def thick_line(self, x0, y0, x1, y1, thickness, color):
        dx = x1 - x0
        dy = y1 - y0
        steps = max(abs(dx), abs(dy), 1)
        for i in range(steps + 1):
            x = x0 + dx * i // steps
            y = y0 + dy * i // steps
            half = thickness // 2
            self.fill_rect(x - half, y - half, thickness, thickness, color)

    def draw_char(self, ch, x, y, scale, color):
        glyph = FONT.get(ch.upper())
        if glyph is None:
            return
        for gy, row in enumerate(glyph):
            for gx, bit in enumerate(row):
                if bit == "1":
                    self.fill_rect(
                        x + gx * scale, y + gy * scale, scale, scale, color
                    )

    def draw_text(self, text, x, y, scale, color):
        cx = x
        for ch in text:
            self.draw_char(ch, cx, y, scale, color)
            cx += char_width(scale)

    def to_png_bytes(self):
        raw = bytearray()
        for row in self.rows:
            raw.append(0)  # filter type 0 (none) for every scanline
            raw.extend(row)
        compressed = zlib.compress(bytes(raw), 9)

        def chunk(tag, data):
            out = struct.pack(">I", len(data))
            out += tag + data
            crc = zlib.crc32(tag + data) & 0xffffffff
            out += struct.pack(">I", crc)
            return out

        sig = b"\x89PNG\r\n\x1a\n"
        ihdr = struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0)
        return (
            sig
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", compressed)
            + chunk(b"IEND", b"")
        )


# ---------------------------------------------------------------------------
# Story data: (category, accent color, icon fn, caption lines)
# Every caption line length is checked against CARD caption width below.
# ---------------------------------------------------------------------------

def icon_diplomacy(img, ix, iy, color, bg):
    icx, icy = ix + 32, iy + 32
    img.fill_circle(icx - 12, icy, 18, color)
    img.fill_circle(icx + 12, icy, 18, color)

def icon_energy(img, ix, iy, color, bg):
    icx = ix + 32
    img.fill_triangle((icx, iy + 4), (ix + 12, iy + 60), (ix + 52, iy + 60), color)
    img.fill_triangle((icx, iy + 22), (ix + 22, iy + 56), (ix + 42, iy + 56), bg)

def icon_rift(img, ix, iy, color, bg):
    img.fill_rect(ix + 4, iy + 20, 22, 24, color)
    img.fill_rect(ix + 38, iy + 20, 22, 24, color)
    img.thick_line(ix + 26, iy + 10, ix + 38, iy + 54, 3, color)

def icon_shipping(img, ix, iy, color, bg):
    img.fill_triangle((ix + 8, iy + 38), (ix + 56, iy + 38), (ix + 46, iy + 54), color)
    img.fill_rect(ix + 8, iy + 34, 48, 4, color)
    img.fill_rect(ix + 29, iy + 8, 3, 26, color)
    img.fill_triangle((ix + 32, iy + 8), (ix + 32, iy + 20), (ix + 46, iy + 14), color)
    for i, yy in enumerate((iy + 46, iy + 52, iy + 58)):
        img.thick_line(ix + 6 + i * 2, yy, ix + 58 - i * 2, yy, 3, color)

def icon_alert(img, ix, iy, color, bg):
    icx = ix + 32
    img.fill_triangle((icx, iy + 6), (ix + 6, iy + 58), (ix + 58, iy + 58), color)
    img.fill_rect(icx - 3, iy + 24, 6, 20, bg)
    img.fill_rect(icx - 3, iy + 48, 6, 6, bg)

def icon_escalation(img, ix, iy, color, bg):
    icx = ix + 32
    img.fill_triangle((icx, iy + 6), (icx - 18, iy + 34), (icx + 18, iy + 34), color)
    img.fill_rect(icx - 6, iy + 34, 12, 26, color)


STORIES = [
    {
        "category": "DIPLOMACY",
        "color": (70, 130, 255),
        "icon": icon_diplomacy,
        "lines": [
            "TRUMP AND NATO CHIEF RUTTE URGE",
            "RUSSIA TO AVOID WIDENING WAR",
            "AFTER TRUMP MET PUTIN AND XI",
        ],
    },
    {
        "category": "ENERGY WAR",
        "color": (255, 140, 40),
        "icon": icon_energy,
        "lines": [
            "UKRAINE TELLS PUTIN TO STOP",
            "COMPLAINING OVER OIL STRIKES",
            "THAT CUT 55% OF RUSSIAN",
            "REFINING AS MOSCOW VOWS REVENGE",
        ],
    },
    {
        "category": "DIPLOMATIC RIFT",
        "color": (190, 90, 255),
        "icon": icon_rift,
        "lines": [
            "NORTH KOREA EXPELS TOP SWISS",
            "DIPLOMAT ORDERS EMBASSY SHUT",
            "OVER SWISS SANCTIONS TIED TO",
            "UKRAINIAN CHILDREN AT NK CAMP",
        ],
    },
    {
        "category": "GULF SECURITY",
        "color": (40, 200, 190),
        "icon": icon_shipping,
        "lines": [
            "IRAN SAYS SHIPS HIT MINES IN",
            "STRAIT OF HORMUZ AMID US",
            "NAVAL BLOCKADE TENSIONS",
            "TEHRAN DEMANDS VESSELS COORDINATE",
        ],
    },
    {
        "category": "MIDEAST ALERT",
        "color": (255, 70, 70),
        "icon": icon_alert,
        "lines": [
            "HOUTHI ATTACK WOUNDS 11 IN",
            "RIYADH FINANCIAL DISTRICT",
            "AS REGIONAL TENSIONS SURGE",
        ],
    },
    {
        "category": "ESCALATION RISK",
        "color": (255, 210, 40),
        "icon": icon_escalation,
        "lines": [
            "US TELLS CITIZENS TO LEAVE",
            "IRAN AMID WARNINGS OF RAPID",
            "ESCALATION ACROSS THE REGION",
        ],
    },
]


def build_image():
    # NOTE: all coordinates below are derived from WIDTH/HEIGHT/MARGIN/GAP
    # constants so the 2x3 card grid stays centered if those are tuned later.
    img = Image(WIDTH, HEIGHT, BG)

    # Title bar
    TITLE_H = 110
    img.fill_rect(0, 0, WIDTH, TITLE_H, TITLE_BAR)
    title = "WORLD NEWS"
    title_scale = 6
    tw = text_width(title, title_scale)
    img.draw_text(title, (WIDTH - tw) // 2, 20, title_scale, WHITE)
    date_str = "NOVEMBER 25 2026"
    date_scale = 3
    dw = text_width(date_str, date_scale)
    img.draw_text(date_str, (WIDTH - dw) // 2, 70, date_scale, DIM)
    # thin accent line under title bar
    img.fill_rect(0, TITLE_H, WIDTH, 3, (60, 90, 170))

    # Grid layout: 2 columns x 3 rows
    MARGIN = 24
    GAP = 20
    COLS, ROWS = 2, 3
    grid_top = TITLE_H + MARGIN
    grid_left = MARGIN
    grid_width = WIDTH - 2 * MARGIN
    grid_height = HEIGHT - grid_top - MARGIN
    card_w = (grid_width - GAP * (COLS - 1)) // COLS
    card_h = (grid_height - GAP * (ROWS - 1)) // ROWS

    ACCENT_W = 8
    PAD = 16
    ICON_SIZE = 64
    content_w = card_w - ACCENT_W - PAD * 2
    label_scale = 2
    caption_scale = 2
    label_x_offset = ICON_SIZE + 12
    label_width = content_w - label_x_offset
    caption_line_h = GLYPH_H * caption_scale + 6

    # Sanity-check text fits before drawing anything (fail loudly if not).
    max_caption_chars = max_chars_for_width(content_w, caption_scale)
    max_label_chars = max_chars_for_width(label_width, label_scale)
    for story in STORIES:
        assert len(story["category"]) <= max_label_chars, story["category"]
        for line in story["lines"]:
            assert len(line) <= max_caption_chars, line

    for idx, story in enumerate(STORIES):
        col = idx % COLS
        row = idx // COLS
        card_x = grid_left + col * (card_w + GAP)
        card_y = grid_top + row * (card_h + GAP)

        img.fill_rect(card_x, card_y, card_w, card_h, CARD_BG)
        img.fill_rect(card_x, card_y, ACCENT_W, card_h, story["color"])

        content_x = card_x + ACCENT_W + PAD
        content_y = card_y + PAD

        # icon
        story["icon"](img, content_x, content_y, story["color"], CARD_BG)

        # category label, vertically centered with the icon box
        label_y = content_y + ICON_SIZE // 2 - (GLYPH_H * label_scale) // 2
        img.draw_text(
            story["category"],
            content_x + label_x_offset,
            label_y,
            label_scale,
            story["color"],
        )

        # caption lines below icon
        text_y = content_y + ICON_SIZE + 14
        for line in story["lines"]:
            img.draw_text(line, content_x, text_y, caption_scale, WHITE)
            text_y += caption_line_h

    return img


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "entry.png")

    img = build_image()
    png_bytes = img.to_png_bytes()

    with open(out_path, "wb") as f:
        f.write(png_bytes)


if __name__ == "__main__":
    main()
