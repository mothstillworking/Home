"""Generates moth.gif: a pixel-art moth circling a hanging light bulb and bonking into it.

Original artwork for Moth Still Working. Run:  python tools/make_moth_gif.py
Writes ../moth.gif (relative to this script). Tweak the constants below and re-run.
"""
import math
from pathlib import Path
from PIL import Image

W, H = 160, 108            # canvas in art pixels (the page scales it up with sharp pixels)
FRAMES = 72                # 72 x 70 ms = ~5 s loop
FRAME_MS = 70
BULB_X, BULB_Y = 80, 46    # bulb centre
BULB_R = 9

# Palette (index -> RGB). Index 0 is the page background (#0d0b1a) so the GIF blends into the page.
PALETTE = [
    (13, 11, 26),     # 0 background
    (24, 18, 34),     # 1 glow 1 (faintest)
    (40, 28, 40),     # 2 glow 2
    (66, 44, 44),     # 3 glow 3
    (104, 72, 50),    # 4 glow 4
    (150, 106, 58),   # 5 glow 5 (brightest halo)
    (255, 210, 110),  # 6 bulb glass
    (255, 246, 214),  # 7 bulb hot core
    (255, 160, 60),   # 8 filament
    (96, 94, 108),    # 9 socket light
    (58, 56, 70),     # 10 socket dark
    (44, 40, 56),     # 11 cord
    (226, 206, 164),  # 12 moth wing
    (156, 132, 98),   # 13 moth wing edge
    (92, 70, 52),     # 14 moth body
    (255, 255, 255),  # 15 spark
]
GLOW_LEVELS = [0, 1, 2, 3, 4, 5]

BAYER4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]

# Moth sprites, top-down. a = antenna, W = wing, d = wing edge, B = body.
MOTH_OPEN = [
    "...a.....a...",
    "....a...a....",
    ".dWW..B..WWd.",
    "dWWWW.B.WWWWd",
    "dWWdWWBWWdWWd",
    ".dWWWWBWWWWd.",
    "..dWWdBdWWd..",
    "...dd.B.dd...",
    "......B......",
]
MOTH_CLOSED = [
    "...a.....a...",
    "....a...a....",
    "...dW.B.Wd...",
    "..dWWWBWWWd..",
    "..dWdWBWdWd..",
    "...dWWBWWd...",
    "....dWBWd....",
    ".....dBd.....",
    "......B......",
]
SPRITE_COLOURS = {"a": 14, "W": 12, "d": 13, "B": 14}


def moth_position(t):
    """Moth centre at loop time t in [0, 1). Two orbits per loop; it hits the bulb at t = 0 and 0.5."""
    phase = 2 * math.pi * 2 * t
    # Distance from the bulb: touching at the hit, swinging wide in between, with a quick recoil.
    approach = 0.5 - 0.5 * math.cos(phase)                 # 0 at hit, 1 farthest
    r = BULB_R + 5 + 30 * approach ** 0.8
    angle = phase + 0.35 * math.sin(phase * 3)             # wobbly, moth-like flight
    x = BULB_X + r * math.cos(angle) * 1.35
    y = BULB_Y + r * math.sin(angle) * 0.75 + 2.5 * math.sin(2 * math.pi * 7 * t)
    behind = math.sin(angle) < 0                           # upper half of the orbit = behind the bulb
    return x, y, behind


def hit_strength(t):
    """1.0 on the frame of a bonk, fading over the next few frames."""
    frame = round(t * FRAMES) % (FRAMES // 2)
    return max(0.0, 1.0 - frame / 4.0)


def draw_glow(px, t):
    flicker = 1.5 * math.sin(2 * math.pi * 3 * t) + 0.8 * math.sin(2 * math.pi * 11 * t)
    radius = 50 + flicker + 10 * hit_strength(t)
    for y in range(H):
        for x in range(W):
            d = math.hypot((x - BULB_X) * 0.9, y - BULB_Y)
            if d >= radius:
                continue
            level = (1 - d / radius) ** 1.25 * (len(GLOW_LEVELS) - 1)
            level *= min(1.0, y / 14)  # fade out at the top edge so it blends into the page
            base = int(level)
            frac = level - base
            if frac * 16 > BAYER4[y % 4][x % 4]:
                base += 1
            px[x, y] = GLOW_LEVELS[min(base, len(GLOW_LEVELS) - 1)]


def draw_bulb(px, t):
    # Cord and socket.
    for y in range(0, BULB_Y - BULB_R - 5):
        px[BULB_X, y] = 11
    for y in range(BULB_Y - BULB_R - 5, BULB_Y - BULB_R + 2):
        for x in range(BULB_X - 4, BULB_X + 5):
            px[x, y] = 9 if (y - (BULB_Y - BULB_R - 5)) % 2 == 0 else 10
    # Glass, hotter in the middle; the core swells when the moth bonks into it.
    core_r = 4.5 + 2 * hit_strength(t)
    for y in range(BULB_Y - BULB_R, BULB_Y + BULB_R + 1):
        for x in range(BULB_X - BULB_R, BULB_X + BULB_R + 1):
            d = math.hypot(x - BULB_X, (y - BULB_Y) * 1.05)
            if d <= BULB_R:
                px[x, y] = 7 if d <= core_r else 6
    # Filament zig-zag.
    for i, dx in enumerate(range(-3, 4)):
        px[BULB_X + dx, BULB_Y - 1 + (i % 2)] = 8


def draw_moth(px, x, y, frame_index):
    sprite = MOTH_OPEN if frame_index % 2 == 0 else MOTH_CLOSED
    left = int(round(x)) - len(sprite[0]) // 2
    top = int(round(y)) - len(sprite) // 2
    for sy, row in enumerate(sprite):
        for sx, ch in enumerate(row):
            if ch == ".":
                continue
            px_x, px_y = left + sx, top + sy
            if 0 <= px_x < W and 0 <= px_y < H:
                px[px_x, px_y] = SPRITE_COLOURS[ch]


def draw_bonk(px, x, y, t):
    strength = hit_strength(t)
    if strength <= 0.3:
        return
    spread = int(round(8 + (1 - strength) * 7))
    for dx, dy in ((-spread, -4), (spread, -5), (0, -spread - 3)):
        cx, cy = int(round(x)) + dx, int(round(y)) + dy
        for ox, oy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            if 0 <= cx + ox < W and 0 <= cy + oy < H:
                px[cx + ox, cy + oy] = 15


def render_frame(i):
    t = i / FRAMES
    image = Image.new("P", (W, H), 0)
    image.putpalette([c for rgb in PALETTE for c in rgb])
    px = image.load()
    draw_glow(px, t)
    x, y, behind = moth_position(t)
    if behind:
        draw_moth(px, x, y, i)
        draw_bulb(px, t)
    else:
        draw_bulb(px, t)
        draw_moth(px, x, y, i)
    draw_bonk(px, x, y, t)
    return image


def main():
    frames = [render_frame(i) for i in range(FRAMES)]
    out = Path(__file__).resolve().parent.parent / "moth.gif"
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=FRAME_MS,
                   loop=0, disposal=1, optimize=False)
    print(f"Wrote {out} ({out.stat().st_size // 1024} KB, {FRAMES} frames)")


if __name__ == "__main__":
    main()
