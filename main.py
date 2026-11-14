"""Tonkotsu ramen, drawn procedurally. Stdlib only, deterministic, no network.

Writes one 1024x1024 PNG to $MAKEFUN_OUTPUT_DIR/entry.png (default /output).
"""
import math
import os
import random
import struct
import zlib

W = 1024
H = 1024
CX, CY = 512, 545  # bowl centre

rnd = random.Random(20261114)


def clamp(v, lo=0, hi=255):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return (int(lerp(c1[0], c2[0], t)), int(lerp(c1[1], c2[1], t)),
            int(lerp(c1[2], c2[2], t)))


# ---------------------------------------------------------------- pixel buffer
pix = bytearray(W * H * 3)


def set_px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        pix[i] = c[0]
        pix[i + 1] = c[1]
        pix[i + 2] = c[2]


def blend_px(x, y, c, a):
    """Blend colour c over pixel (x, y) with alpha a (0..1)."""
    if 0 <= x < W and 0 <= y < H and a > 0:
        i = (y * W + x) * 3
        if a >= 1:
            pix[i] = c[0]
            pix[i + 1] = c[1]
            pix[i + 2] = c[2]
        else:
            pix[i] = int(pix[i] + (c[0] - pix[i]) * a)
            pix[i + 1] = int(pix[i + 1] + (c[1] - pix[i + 1]) * a)
            pix[i + 2] = int(pix[i + 2] + (c[2] - pix[i + 2]) * a)


def fill_circle(cx, cy, r, c, a=1.0):
    r2 = r * r
    y0 = max(0, int(cy - r))
    y1 = min(H - 1, int(cy + r) + 1)
    for y in range(y0, y1):
        dy = y - cy
        dx = int(math.sqrt(max(0, r2 - dy * dy)))
        x0 = max(0, int(cx - dx))
        x1 = min(W - 1, int(cx + dx))
        if a >= 1:
            for x in range(x0, x1 + 1):
                i = (y * W + x) * 3
                pix[i] = c[0]
                pix[i + 1] = c[1]
                pix[i + 2] = c[2]
        else:
            for x in range(x0, x1 + 1):
                blend_px(x, y, c, a)


def fill_ellipse(cx, cy, rx, ry, c, a=1.0):
    y0 = max(0, int(cy - ry))
    y1 = min(H - 1, int(cy + ry) + 1)
    for y in range(y0, y1):
        dy = (y - cy) / ry
        dx = int(rx * math.sqrt(max(0.0, 1.0 - dy * dy)))
        x0 = max(0, int(cx - dx))
        x1 = min(W - 1, int(cx + dx))
        for x in range(x0, x1 + 1):
            if a >= 1:
                set_px(x, y, c)
            else:
                blend_px(x, y, c, a)


def ring(cx, cy, r, thick, c, a=1.0):
    """Outline circle (a ring)."""
    y0 = max(0, int(cy - r - thick))
    y1 = min(H - 1, int(cy + r + thick) + 1)
    for y in range(y0, y1):
        dy = y - cy
        for x in range(max(0, int(cx - r - thick)),
                       min(W - 1, int(cx + r + thick)) + 1):
            d = math.hypot(x - cx, dy)
            if abs(d - r) <= thick:
                if a >= 1:
                    set_px(x, y, c)
                else:
                    blend_px(x, y, c, a)


def thick_line(x0, y0, x1, y1, half, c, a=1.0):
    """Thick line as a chain of small filled circles."""
    length = math.hypot(x1 - x0, y1 - y0)
    steps = max(2, int(length / 3))
    for s in range(steps + 1):
        t = s / steps
        fill_circle(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, half, c, a)


def rounded_rect(x0, y0, x1, y1, r, c, a=1.0):
    for y in range(max(0, y0), min(H, y1 + 1)):
        for x in range(max(0, x0), min(W, x1 + 1)):
            # rounded corners: skip pixels outside corner circles
            cx = min(max(x, x0 + r), x1 - r)
            cy = min(max(y, y0 + r), y1 - r)
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r + 1:
                if a >= 1:
                    set_px(x, y, c)
                else:
                    blend_px(x, y, c, a)


# ---------------------------------------------------------------- background
# Dark wooden table: warm vertical gradient + subtle grain.
grain_col = [0.92 + 0.08 * math.sin(x * 0.021 + 1.7 * math.sin(x * 0.004))
             for x in range(W)]
for y in range(H):
    t = y / (H - 1)
    base = mix((74, 48, 30), (26, 16, 10), t)
    # warm window light from the upper left
    glow = max(0.0, 1.0 - math.hypot((0 - 180) / 900.0, (y - 120) / 900.0))
    light = 1.0 + 0.22 * glow
    row = y * W * 3
    for x in range(W):
        g = grain_col[x]
        i = row + x * 3
        pix[i] = clamp(int(base[0] * g * light))
        pix[i + 1] = clamp(int(base[1] * g * light))
        pix[i + 2] = clamp(int(base[2] * g * light))
# a few darker plank seams
for sy in (250, 800):
    for x in range(W):
        blend_px(x, sy + int(2 * math.sin(x * 0.01)), (18, 11, 7), 0.5)

# soft shadow under the bowl
for y in range(CY + 180, min(H, CY + 430)):
    for x in range(CX - 430, CX + 431):
        d = math.hypot((x - CX) / 430.0, (y - (CY + 300)) / 130.0)
        if d < 1:
            blend_px(x, y, (0, 0, 0), 0.38 * (1 - d))

# ---------------------------------------------------------------- bowl
fill_circle(CX, CY, 395, (24, 22, 28))          # outer bowl
fill_circle(CX, CY, 395, (70, 60, 80), 0.18)   # faint sheen top-left
fill_circle(CX, CY, 378, (196, 172, 138))       # rim
fill_circle(CX, CY, 356, (168, 142, 108))       # inner rim shadow
# bowl body shading: darker at bottom, warm highlight upper left
for y in range(CY - 395, CY + 396):
    for x in range(CX - 395, CX + 396):
        d = math.hypot(x - CX, y - CY)
        if 356 < d <= 395:
            t = (d - 356) / 39.0
            shade = 1.0 - 0.45 * t
            hi = max(0.0, 1.0 - math.hypot((x - 380) / 300.0, (y - 380) / 300.0))
            i = (y * W + x) * 3
            pix[i] = clamp(int(pix[i] * shade + 60 * hi))
            pix[i + 1] = clamp(int(pix[i + 1] * shade + 48 * hi))
            pix[i + 2] = clamp(int(pix[i + 2] * shade + 40 * hi))

# ---------------------------------------------------------------- broth
BR = 348
for y in range(CY - BR, CY + BR + 1):
    for x in range(CX - BR, CX + BR + 1):
        dx, dy = x - CX, y - CY
        d = math.hypot(dx, dy)
        if d <= BR:
            t = d / BR
            c = mix((238, 210, 160), (172, 128, 78), t * t)
            # gentle swirls in the broth
            sw = 0.5 + 0.5 * math.sin(d * 0.045 - math.atan2(dy, dx) * 3.0)
            c = mix(c, (246, 224, 178), sw * 0.16)
            # warm light from upper left
            gl = max(0.0, 1.0 - math.hypot((x - 400) / 420.0, (y - 420) / 420.0))
            c = (clamp(int(c[0] + 26 * gl)), clamp(int(c[1] + 18 * gl)),
                 clamp(int(c[2] + 8 * gl)))
            set_px(x, y, c)
# glossy oil sheen on the broth
fill_ellipse(430, 440, 120, 46, (255, 226, 170), 0.16)
fill_ellipse(620, 660, 90, 34, (255, 220, 160), 0.10)

# ---------------------------------------------------------------- noodles
NOODLE = (240, 206, 132)
NOODLE_D = (198, 156, 84)
for strand in range(46):
    bx = CX - 300 + rnd.random() * 600
    by = CY - 260 + rnd.random() * 520
    amp = 14 + rnd.random() * 26
    freq = 0.018 + rnd.random() * 0.02
    phase = rnd.random() * 6.28
    length = 120 + rnd.random() * 190
    direction = rnd.choice([1, -1])
    px0 = py0 = None
    for s in range(0, int(length), 6):
        t = s / length
        x = bx + direction * s
        y = by + amp * math.sin(s * freq * 6.28 + phase) * (1 - 0.4 * t)
        if math.hypot(x - CX, y - CY) < BR - 12:
            if px0 is not None:
                thick_line(px0, py0, x, y, 5.0, NOODLE_D, 0.95)
                thick_line(px0, py0 - 2, x, y - 2, 3.6, NOODLE, 0.95)
            px0, py0 = x, y
        else:
            px0 = py0 = None
# a lifted bundle of noodles, draped over the rim (the hero detail)
for k in range(5):
    px0 = py0 = None
    for s in range(0, 240, 6):
        t = s / 240.0
        x = 640 + k * 11 + s * 0.55
        y = 185 + 24 * math.sin(s * 0.045 + k * 0.9) + 130 * t
        if px0 is not None:
            thick_line(px0, py0, x, y, 6.0, NOODLE_D, 0.97)
            thick_line(px0, py0 - 2, x, y - 2, 4.2, NOODLE, 0.97)
        px0, py0 = x, y

# ---------------------------------------------------------------- chili oil
# glossy red-orange drizzle on the broth for colour contrast and appetite
for k in range(7):
    ox = CX - 220 + rnd.random() * 440
    oy = CY - 220 + rnd.random() * 440
    if math.hypot(ox - CX, oy - CY) > BR - 60:
        continue
    fill_ellipse(ox, oy, 26 + rnd.random() * 22, 10 + rnd.random() * 8,
                 (198, 62, 22), 0.55)
    fill_ellipse(ox - 6, oy - 3, 14 + rnd.random() * 10, 5,
                 (232, 96, 32), 0.6)
    fill_ellipse(ox - 8, oy - 4, 8, 3, (255, 150, 70), 0.7)
def chashu(cx, cy, r):
    fill_circle(cx, cy, r, (122, 74, 50))
    fill_circle(cx, cy, r - 7, (196, 128, 96))
    fill_circle(cx, cy, int(r * 0.62), (232, 158, 136))
    fill_circle(cx, cy, int(r * 0.38), (246, 196, 176))
    # fat marbling arcs
    for k in range(5):
        a0 = rnd.random() * 6.28
        a1 = a0 + 0.7 + rnd.random() * 0.8
        rr = r * (0.45 + 0.18 * rnd.random())
        steps = 14
        for s in range(steps + 1):
            a = a0 + (a1 - a0) * s / steps
            fill_circle(cx + rr * math.cos(a), cy + rr * math.sin(a),
                        3.5, (248, 220, 200), 0.85)
    fill_circle(cx - r * 0.3, cy - r * 0.35, r * 0.2, (255, 235, 220), 0.35)


chashu(380, 640, 108)
chashu(640, 430, 98)

# ---------------------------------------------------------------- soft egg
def egg(cx, cy):
    fill_ellipse(cx, cy, 92, 78, (250, 244, 230))
    fill_ellipse(cx, cy, 86, 72, (244, 236, 218))
    # jammy yolk, slightly domed
    for y in range(cy - 52, cy + 53):
        for x in range(cx - 56, cx + 57):
            d = math.hypot((x - cx) / 56.0, (y - cy) / 52.0)
            if d <= 1:
                c = mix((255, 176, 62), (226, 116, 26), d)
                gl = max(0.0, 1.0 - math.hypot((x - (cx - 18)) / 34.0,
                                              (y - (cy - 16)) / 30.0))
                c = (clamp(int(c[0] + 30 * gl)), clamp(int(c[1] + 18 * gl)),
                     clamp(int(c[2] + 6 * gl)))
                set_px(x, y, c)
    fill_ellipse(cx - 16, cy - 18, 20, 12, (255, 214, 130), 0.55)


egg(660, 660)

# ---------------------------------------------------------------- spring onion
for _ in range(26):
    ox = CX - 300 + rnd.random() * 600
    oy = CY - 300 + rnd.random() * 600
    if math.hypot(ox - CX, oy - CY) > BR - 18:
        continue
    r = 7 + rnd.random() * 7
    ring(ox, oy, r, 2.6, (52, 128, 52), 0.95)
    ring(ox, oy, r, 1.2, (168, 214, 120), 0.9)
    fill_circle(ox, oy, r * 0.35, (120, 180, 90), 0.7)

# ---------------------------------------------------------------- nori
rounded_rect(300, 330, 372, 470, 10, (26, 34, 26))
rounded_rect(306, 336, 366, 464, 8, (38, 48, 36))
for k in range(4):
    thick_line(318, 350 + k * 30, 354, 350 + k * 30, 1.5, (58, 72, 54), 0.6)

# ---------------------------------------------------------------- sesame
for _ in range(40):
    sx = CX - 300 + rnd.random() * 600
    sy = CY - 300 + rnd.random() * 600
    if math.hypot(sx - CX, sy - CY) > BR - 14:
        continue
    fill_ellipse(sx, sy, 4.5, 2.6, (250, 232, 190), 0.95)

# ---------------------------------------------------------------- chopsticks
thick_line(700, 210, 1010, 330, 9, (148, 92, 48))
thick_line(688, 238, 1000, 358, 9, (132, 80, 42))
thick_line(700, 210, 1010, 330, 3.5, (196, 132, 74), 0.8)
thick_line(688, 238, 1000, 358, 3.5, (178, 118, 64), 0.8)

# ---------------------------------------------------------------- steam
for band in range(5):
    bx = 380 + band * 62
    for y in range(60, 330):
        t = (330 - y) / 270.0
        wob = 26 * math.sin(y * 0.03 + band * 1.9)
        for x in range(int(bx + wob - 30), int(bx + wob + 31)):
            dd = abs(x - (bx + wob)) / 30.0
            if dd < 1:
                blend_px(x, y, (255, 250, 240),
                         0.14 * (1 - dd) * (0.4 + 0.6 * t))

# ---------------------------------------------------------------- vignette
for y in range(H):
    for x in range(W):
        d = math.hypot((x - CX) / 720.0, (y - CY) / 720.0)
        if d > 0.72:
            blend_px(x, y, (10, 6, 4), min(0.42, (d - 0.72) * 1.1))


# ---------------------------------------------------------------- PNG encoder
def chunk(ctype, data):
    out = struct.pack(">I", len(data)) + ctype + data
    out += struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)
    return out


def write_png(path):
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: none
        raw += pix[y * W * 3:(y + 1) * W * 3]
    idat = zlib.compress(bytes(raw), 6)
    data = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", idat) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "entry.png")
    size = write_png(path)
    print(f"wrote {path} ({W}x{H}, {size} bytes)")


if __name__ == "__main__":
    main()
