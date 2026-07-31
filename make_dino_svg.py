#!/usr/bin/env python3
"""
Animated ASCII Chrome-dino runner as a self-contained SVG.

The scene is built from three scrolling layers plus a fixed dino:
  stars   - slow parallax, own loop
  ground  - dashes and bumps, scrolls at run speed
  cacti   - same speed as ground, spaced so the pattern tiles seamlessly
  dino    - fixed x, alternating leg frames, translateY for the jumps

Tiling trick: the cactus/ground track is 2x the repeat width with obstacles
placed every REPEAT/2 columns, and it translates left by exactly REPEAT
columns per loop. At the reset the next cactus is already where the last one
was, so the loop is invisible.

Jump timing is derived from when each cactus reaches the dino's column, so
the dino always clears them instead of running through them.
"""

import random

COLS, ROWS = 110, 16
CW, CH = 8.0, 14.0          # character cell
GROUND_ROW = 13
DINO_COL = 12
REPEAT = 120                # columns per scroll cycle
LOOP = 6.0                  # seconds per scroll cycle
JUMP_ROWS = 5
DISPLAY_W = 820

FONT = ("ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,"
        "'Liberation Mono',monospace")

FG = "#e6edf3"
DIM = "#6e7681"
STAR = "#3d444d"
BG = "#0d1117"

# --- sprites ---------------------------------------------------------------
# 21 wide, 12 tall. Tail on the left, head on the right, as in Chrome's.
DINO_BODY = [
    "              ██████ ",
    "             ████████",
    "             ██ █████",
    "             ████████",
    "             ██████  ",
    "  ██         ███████ ",
    "  ███      ██████████",
    "  ██████████████████ ",
    "   ██████████████    ",
    "    ███████████      ",
]
LEGS_A = [
    "     ███   ██        ",
    "     ██     ███      ",
]
LEGS_B = [
    "     ███   ███       ",
    "      ███   ██       ",
]
CACTUS_S = [
    "  ██  ",
    "  ██  ",
    "█ ██  ",
    "█ ██ █",
    "██████",
    "  ██  ",
]
CACTUS_L = [
    "   ██   ",
    "   ██ █ ",
    "█  ██ █ ",
    "█  ████ ",
    "██████  ",
    "   ██   ",
]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def sprite(lines, col, top_row, fill, cls=""):
    """Emit one <text> per sprite row at a character grid position."""
    out = []
    c = f' class="{cls}"' if cls else ""
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        y = (top_row + i + 1) * CH - 3
        out.append(f'<text{c} x="{col * CW:.1f}" y="{y:.1f}" '
                   f'fill="{fill}">{esc(line)}</text>')
    return "\n".join(out)


def build():
    rnd = random.Random(7)

    # ---- stars (two tiles wide so the parallax loop is seamless) ----
    stars = []
    for _ in range(70):
        c = rnd.randrange(0, REPEAT * 2)
        r = rnd.randrange(0, GROUND_ROW - 3)
        stars.append((c, r, rnd.choice([".", ".", "·", "*"])))
    star_txt = "\n".join(
        f'<text x="{c * CW:.1f}" y="{(r + 1) * CH - 3:.1f}" '
        f'fill="{STAR}">{ch}</text>' for c, r, ch in stars)

    # ---- ground: dashes with occasional bumps, tiled over 2x REPEAT ----
    row = []
    i = 0
    while i < REPEAT * 2:
        if rnd.random() < 0.08:
            row.append("▂")
        else:
            row.append("_" if rnd.random() < 0.72 else " ")
        i += 1
    ground = (f'<text x="0" y="{(GROUND_ROW + 1) * CH - 3:.1f}" '
              f'fill="{DIM}">{esc("".join(row))}</text>')

    # ---- cacti: one every REPEAT/2 columns so the track tiles ----
    cacti = []
    obstacle_cols = []
    for k in range(4):                       # covers 2 x REPEAT
        col = 30 + k * (REPEAT // 2)
        art = CACTUS_L if k % 2 else CACTUS_S
        top = GROUND_ROW - len(art)
        cacti.append(sprite(art, col, top, FG))
        obstacle_cols.append(col)
    cacti_txt = "\n".join(cacti)

    # ---- jump timing: when does each cactus reach the dino column? ----
    # track offset goes 0 -> -REPEAT over LOOP seconds (linear)
    speed = REPEAT / LOOP                    # columns per second
    hits = []
    for col in obstacle_cols:
        t = (col - DINO_COL) / speed
        if 0 <= t <= LOOP:
            hits.append(t)
    hits.sort()

    # Sample a parabola across the airborne window. A bare three-point tween
    # under linear timing reads as a triangular hop; sampling gives real
    # ballistic weight (fast off the ground, hangs at the apex).
    air = 0.80                               # seconds off the ground
    SAMPLES = 9
    keys = [(0.0, 0)]
    for t in hits:
        for i in range(SAMPLES + 1):
            u = i / SAMPLES                  # 0..1 across the jump
            y = -JUMP_ROWS * (1 - (2 * u - 1) ** 2)
            keys.append((t - air / 2 + u * air, y))
    keys.append((LOOP, 0))
    keys.sort(key=lambda k: k[0])

    seen, frames = set(), []
    for t, v in keys:
        pct = round(max(0.0, min(100.0, t / LOOP * 100)), 2)
        if pct in seen:
            continue
        seen.add(pct)
        frames.append(f"{pct}%{{transform:translateY({v * CH:.2f}px)}}")
    jump_kf = "".join(frames)

    dino_top = GROUND_ROW - 12
    body = sprite(DINO_BODY, DINO_COL, dino_top, FG)
    legs_a = sprite(LEGS_A, DINO_COL, dino_top + 10, FG, "la")
    legs_b = sprite(LEGS_B, DINO_COL, dino_top + 10, FG, "lb")

    w, h = COLS * CW, ROWS * CH
    track_px = REPEAT * CW

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" width="{DISPLAY_W}" height="{DISPLAY_W * h / w:.1f}" role="img" aria-label="ASCII dino runner">
<style>
text{{font-family:{FONT};font-size:{CH * 0.86:.1f}px;white-space:pre}}
.scroll{{animation:roll {LOOP}s linear infinite}}
@keyframes roll{{from{{transform:translateX(0)}}to{{transform:translateX(-{track_px:.1f}px)}}}}
.stars{{animation:roll {LOOP * 4}s linear infinite}}
#dino{{animation:jump {LOOP}s linear infinite}}
@keyframes jump{{{jump_kf}}}
.la{{animation:stepa .34s steps(1,end) infinite}}
.lb{{animation:stepb .34s steps(1,end) infinite}}
@keyframes stepa{{0%,50%{{opacity:1}}50.01%,100%{{opacity:0}}}}
@keyframes stepb{{0%,50%{{opacity:0}}50.01%,100%{{opacity:1}}}}
@media(prefers-reduced-motion:reduce){{
.scroll,.stars,#dino,.la,.lb{{animation:none}}.lb{{opacity:0}}}}
</style>
<rect width="100%" height="100%" fill="{BG}"/>
<g class="stars">
{star_txt}
</g>
<g class="scroll">
{ground}
{cacti_txt}
</g>
<g id="dino">
{body}
{legs_a}
{legs_b}
</g>
</svg>'''


if __name__ == "__main__":
    svg = build()
    with open("dino.svg", "w") as f:
        f.write(svg)
    print("dino.svg", len(svg), "bytes")
