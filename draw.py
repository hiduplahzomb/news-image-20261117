#!/usr/bin/env python3
"""Stdlib-only 2D drawing engine: RGB canvas, vector-ish primitives, a
grayscale bitmap font renderer (reads font.bin, built from DejaVu Sans),
and a deterministic PNG encoder. No third-party imports, no network.
"""

import binascii
import math
import os
import struct
import zlib


# ---------------------------------------------------------------- font ----

class FontFace:
    """One face (regular/bold) rasterized at SIZE px in font.bin."""

    def __init__(self, data, offset):
        size_px, count = struct.unpack_from("<II", data, offset)
        offset += 8
        self.size_px = size_px
        self.glyphs = {}
        for _ in range(count):
            cp, adv, bx, by, w, h, off, ln = struct.unpack_from(
                "<IhhhHHII", data, offset)
            offset += 24
            self.glyphs[cp] = (adv, bx, by, w, h, data[off:off + ln])
        # Space advance comes from its glyph record (empty bitmap).
        self.space_advance = self.glyphs.get(32, (0, 0, 0, 0, 0, b""))[0]


class Font:
    """Two faces (index 0 regular, 1 bold) with resampling + caching."""

    def __init__(self, path):
        with open(path, "rb") as f:
            data = f.read()
        if data[:5] != b"MFNT1":
            raise ValueError("bad font file")
        n_faces = struct.unpack_from("<I", data, 8)[0]
        self.faces = []
        offset = 12
        for _ in range(n_faces):
            size_px, count = struct.unpack_from("<II", data, offset)
            self.faces.append(FontFace(data, offset))
            offset = self._face_end(data, offset, count)
        self._cache = {}

    @staticmethod
    def _face_end(data, face_offset, count):
        """End of a face's bitmap block, from its glyph records."""
        rec = face_offset + 8
        end = rec + count * 24
        for i in range(count):
            # Record is "<IhhhHHII" (22 bytes) at a 24-byte stride;
            # bitmap offset/len sit at bytes 14 and 18.
            off, ln = struct.unpack_from("<II", data, rec + i * 24 + 14)
            end = max(end, off + ln)
        return end

    def _resample(self, bmp, w, h, tw, th):
        """Area-average resample of a grayscale bitmap to tw x th."""
        if tw <= 0 or th <= 0 or w <= 0 or h <= 0:
            return b""
        if (w, h) == (tw, th):
            return bytes(bmp)
        # Horizontal pass: each row w -> tw.
        xw = _axis_weights(w, tw)
        rows = []
        for y in range(h):
            row = bmp[y * w:(y + 1) * w]
            out_row = bytearray(tw)
            for dx, ws in enumerate(xw):
                acc = 0.0
                for sx, wt in ws:
                    acc += row[sx] * wt
                out_row[dx] = int(acc + 0.5)
            rows.append(out_row)
        # Vertical pass: h rows -> th.
        yw = _axis_weights(h, th)
        out = bytearray(tw * th)
        for dy, ws in enumerate(yw):
            for dx in range(tw):
                acc = 0.0
                for sy, wt in ws:
                    acc += rows[sy][dx] * wt
                out[dy * tw + dx] = int(acc + 0.5)
        return bytes(out)

    def glyph_at(self, bold, ch, size):
        """Resampled glyph for (bold, char, size_px).

        Returns (advance, bearing_x, bearing_y, width, height, bitmap).
        """
        key = (bold, ch, size)
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        face = self.faces[1 if bold else 0]
        cp = ord(ch)
        rec = face.glyphs.get(cp)
        if rec is None:
            rec = face.glyphs.get(63)  # "?"
        adv, bx, by, w, h, bmp = rec
        scale = size / face.size_px
        tw = max(0, int(round(w * scale)))
        th = max(0, int(round(h * scale)))
        out = (int(round(adv * scale)), int(round(bx * scale)),
               int(round(by * scale)), tw, th,
               self._resample(bmp, w, h, tw, th) if tw and th else b"")
        self._cache[key] = out
        return out

    def measure(self, text, size, bold=False):
        """Width in px of text at the given size."""
        total = 0
        for ch in text:
            total += self.glyph_at(bold, ch, size)[0]
        return total

    def wrap(self, text, size, width, bold=False):
        """Greedy word wrap; returns a list of lines."""
        lines = []
        for para in text.split("\n"):
            words = para.split(" ")
            line = ""
            for word in words:
                trial = word if not line else line + " " + word
                if self.measure(trial, size, bold) <= width or not line:
                    line = trial
                else:
                    lines.append(line)
                    line = word
            if line or not lines:
                lines.append(line)
        return lines


def _axis_weights(src_n, dst_n):
    """Per destination pixel, the (source index, weight) box-filter taps."""
    scale = src_n / dst_n
    out = []
    for d in range(dst_n):
        s0 = d * scale
        s1 = s0 + scale
        i0 = int(math.floor(s0))
        i1 = int(math.ceil(s1))
        ws = []
        for i in range(i0, min(i1, src_n)):
            lo = max(s0, float(i))
            hi = min(s1, float(i + 1))
            w = hi - lo
            if w > 0:
                ws.append((i, w / scale))
        out.append(ws)
    return out


# -------------------------------------------------------------- canvas ----

class Canvas:
    """RGB canvas backed by a bytearray."""

    def __init__(self, width, height, bg):
        self.w = width
        self.h = height
        self.buf = bytearray(bytes(bg) * (width * height))

    def _idx(self, x, y):
        return (y * self.w + x) * 3

    def rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            off = self._idx(x0, yy)
            self.buf[off:off + len(row)] = row

    def rounded_rect(self, x, y, w, h, r, color):
        r = min(r, w // 2, h // 2)
        # Middle band.
        self.rect(x, y + r, w, h - 2 * r, color)
        # Top and bottom bands with corner cut-outs.
        for yy in range(y, y + r):
            dy = r - (yy - y) - 0.5
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            self.rect(x + r - dx, yy, w - 2 * (r - dx), 1, color)
        for yy in range(y + h - r, y + h):
            dy = (yy - (y + h - r)) + 0.5
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            self.rect(x + r - dx, yy, w - 2 * (r - dx), 1, color)

    def circle(self, cx, cy, r, color):
        for yy in range(max(0, cy - r), min(self.h, cy + r + 1)):
            dy = yy - cy
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            self.rect(cx - dx, yy, 2 * dx + 1, 1, color)

    def ring(self, cx, cy, r, width, color):
        for yy in range(max(0, cy - r), min(self.h, cy + r + 1)):
            dy = yy - cy
            outer = int(math.sqrt(max(0, r * r - dy * dy)))
            inner_sq = (r - width) * (r - width) - dy * dy
            inner = int(math.sqrt(max(0, inner_sq))) if inner_sq > 0 else -1
            self.rect(cx - outer, yy, outer - inner, 1, color)
            self.rect(cx + inner + 1, yy, outer - inner, 1, color)

    def line(self, x0, y0, x1, y1, color, width=1):
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        r = max(0, width // 2)
        for i in range(steps + 1):
            t = i / steps
            x = int(round(x0 + (x1 - x0) * t))
            y = int(round(y0 + (y1 - y0) * t))
            if r <= 0:
                if 0 <= x < self.w and 0 <= y < self.h:
                    off = self._idx(x, y)
                    self.buf[off:off + 3] = bytes(color)
            else:
                self.circle(x, y, r, color)

    def polygon(self, points, color):
        """Scanline fill, even-odd rule."""
        if len(points) < 3:
            return
        ys = [p[1] for p in points]
        y0 = max(0, min(ys))
        y1 = min(self.h - 1, max(ys))
        edges = []
        n = len(points)
        for i in range(n):
            x0, yy0 = points[i]
            x1, yy1 = points[(i + 1) % n]
            if yy0 != yy1:
                edges.append((x0, yy0, x1, yy1))
        for y in range(y0, y1 + 1):
            xs = []
            for (x0, yy0, x1, yy1) in edges:
                if min(yy0, yy1) <= y < max(yy0, yy1):
                    t = (y - yy0) / (yy1 - yy0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                xa = int(math.ceil(xs[i]))
                xb = int(math.floor(xs[i + 1]))
                if xb >= xa:
                    self.rect(xa, y, xb - xa + 1, 1, color)

    def ellipse_outline(self, cx, cy, rx, ry, color, width=1):
        steps = max(24, int(2 * math.pi * max(rx, ry) / 2))
        prev = None
        for i in range(steps + 1):
            a = 2 * math.pi * i / steps
            x = int(round(cx + rx * math.cos(a)))
            y = int(round(cy + ry * math.sin(a)))
            if prev is not None:
                self.line(prev[0], prev[1], x, y, color, width)
            prev = (x, y)

    # ------------------------------------------------------------ text ----

    def text(self, font, x, y_baseline, s, size, color, bold=False):
        """Draw text with its baseline at y_baseline. Returns end x."""
        cx = x
        for ch in s:
            adv, bx, by, w, h, bmp = font.glyph_at(bold, ch, size)
            if w and h:
                self._blit(cx + bx, y_baseline - by, w, h, bmp, color)
            cx += adv
        return cx

    def text_centered(self, font, cx, y_baseline, s, size, color,
                      bold=False):
        w = font.measure(s, size, bold)
        return self.text(font, cx - w // 2, y_baseline, s, size, color,
                         bold)

    def _blit(self, x, y, w, h, bmp, color):
        r, g, b = color
        buf = self.buf
        W = self.w
        for yy in range(h):
            py = y + yy
            if py < 0 or py >= self.h:
                continue
            row_off = py * W * 3
            brow = yy * w
            for xx in range(w):
                a = bmp[brow + xx]
                if a == 0:
                    continue
                px = x + xx
                if px < 0 or px >= W:
                    continue
                off = row_off + px * 3
                if a == 255:
                    buf[off] = r
                    buf[off + 1] = g
                    buf[off + 2] = b
                else:
                    ia = 255 - a
                    buf[off] = (r * a + buf[off] * ia) // 255
                    buf[off + 1] = (g * a + buf[off + 1] * ia) // 255
                    buf[off + 2] = (b * a + buf[off + 2] * ia) // 255


# ----------------------------------------------------------------- png ----

def _chunk(kind, payload):
    out = struct.pack(">I", len(payload)) + kind + payload
    out += struct.pack(">I", binascii.crc32(kind + payload) & 0xFFFFFFFF)
    return out


def write_png(path, canvas):
    """Deterministic PNG: filter 0, zlib level 9, no ancillary chunks."""
    w, h = canvas.w, canvas.h
    stride = w * 3
    raw = bytearray()
    raw_append = raw.append
    buf = canvas.buf
    for y in range(h):
        raw_append(0)
        raw += buf[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    data = (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", comp) + _chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


def font_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "font.bin")
