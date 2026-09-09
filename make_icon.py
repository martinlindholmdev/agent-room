#!/usr/bin/env python3
"""Draw the home-screen icon: a terminal prompt mark, no dependencies."""

import math
import struct
import zlib
import os

SIZE = 180
BG = (23, 24, 21)
TEAL = (111, 179, 156)
DIM = (146, 143, 135)


def dist_to_segment(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy
    t = 0.0 if length == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def coverage(distance, radius, soft=1.1):
    if distance <= radius - soft:
        return 1.0
    if distance >= radius + soft:
        return 0.0
    return (radius + soft - distance) / (2 * soft)


def rounded_rect_alpha(x, y, w, h, r):
    cx = min(max(x, r), w - r)
    cy = min(max(y, r), h - r)
    return coverage(math.hypot(x - cx, y - cy), r)


def blend(base, colour, alpha):
    return tuple(int(round(base[i] * (1 - alpha) + colour[i] * alpha)) for i in range(3))


rows = []
for y in range(SIZE):
    row = bytearray([0])
    for x in range(SIZE):
        px, py = x + 0.5, y + 0.5
        outer = rounded_rect_alpha(px, py, SIZE, SIZE, 40)
        pixel = BG

        chevron = min(
            dist_to_segment(px, py, 58, 56, 99, 90),
            dist_to_segment(px, py, 99, 90, 58, 124),
        )
        pixel = blend(pixel, TEAL, coverage(chevron, 7.5))

        bar = dist_to_segment(px, py, 112, 122, 138, 122)
        pixel = blend(pixel, DIM, coverage(bar, 4.5))

        row += bytes(pixel) + bytes([int(round(255 * outer))])
    rows.append(bytes(row))


def chunk(tag, payload):
    return (struct.pack(">I", len(payload)) + tag + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))


png = b"\x89PNG\r\n\x1a\n"
png += chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0))
png += chunk(b"IDAT", zlib.compress(b"".join(rows), 9))
png += chunk(b"IEND", b"")

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
with open(out, "wb") as fh:
    fh.write(png)
print("wrote %s (%d bytes)" % (out, len(png)))
