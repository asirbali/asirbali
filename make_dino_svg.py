#!/usr/bin/env python3
"""
Animated ASCII Chrome-dino runner as a self-contained SVG.

Layers, back to front:
  stars   - slow parallax, own loop
  ground  - dashes and bumps, scrolls at run speed
  cacti   - same speed as ground, spaced so the pattern tiles seamlessly
  dino    - fixed x, alternating leg frames, translateY for the jumps

Tiling: the scroll track is 2x the repeat width with an obstacle every
REPEAT/2 columns, and it translates left by exactly REPEAT columns per loop.
At the reset the next cactus already occupies the previous one's position, so
the seam is invisible.

Jump timing is derived, not guessed. For each cactus we compute the exact
window where its box overlaps the dino's box, then size the jump so the dino
is above the cactus for that entire window. The arc is a parabola sampled
into keyframes, and a parabola of height J only exceeds height H for
sqrt(1 - H/J) of its duration -- so the airborne time has to be scaled by
that factor or the dino clips the cactus on the way up and down.

check() re-simulates the emitted CSS and asserts zero collisions.
"""

import math
import random

COLS, ROWS = 110, 22
CW, CH = 8.0, 14.0
GROUND_ROW = 20
DINO_COL = 12
REPEAT = 180                 # columns per scroll cycle
LOOP = 6.0                   # seconds per scroll cycle
JUMP_ROWS = 9
CACTUS_PHASE = 70            # keeps obstacles clear of the dino at t=0
MARGIN = 1.15                # safety factor on the airborne window
DISPLAY_W = 820

FONT = ("ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,"
        "'Liberation Mono',monospace")
FG, DIM, STAR, BG = "#e6edf3", "#6e7681", "#3d444d", "#0d1117"

# --- sprites ---------------------------------------------------------------
DINO_BODY = [
    "            ███████ ",
    "            ██ █████",
    "            ███████ ",
    "            ██      ",
    "  █         ████████",
    "  ██      ██████████",
    "  ██████████████████",
    "   ████████████████ ",
    "    ██████████████  ",
]
LEGS_A = [
    "     ███    ███     ",
    "     ██      ███    ",
]
LEGS_B = [
    "     ███    ███     ",
    "      ███   ██      ",
]
DINO_W = 20
DINO_H = len(DINO_BODY) + len(LEGS_A)

CACTUS_S = [
    "  ██  ",
    "█ ██ █",
    "██████",
    "  ██  ",
]
CACTUS_L = [
    "   ██   ",
    "█  ██ █ ",
    "██████  ",
    "   ██   ",
]
CACTI = [CACTUS_S, CACTUS_L]
CACTUS_H = max(len(c) for c in CACTI)

assert JUMP_ROWS > CACTUS_H, "jump must exceed cactus height"
assert GROUND_ROW - DINO_H - JUMP_ROWS >= 0, "dino leaves the canvas at apex"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def sprite(lines, col, top_row, fill, cls=""):
    out, c = [], (f' class="{cls}"' if cls else "")
    for i, line in enumerate(lines):
        if line.strip():
            out.append(f'<text{c} x="{col * CW:.1f}" '
                       f'y="{(top_row + i + 1) * CH - 3:.1f}" '
                       f'fill="{fill}">{esc(line)}</text>')
    return "\n".join(out)


def obstacles():
    """(track column, art) for every cactus across two repeats."""
    return [(CACTUS_PHASE + k * (REPEAT // 2), CACTI[k % len(CACTI)])
            for k in range(4)]


def jump_keys():
    """Keyframe list (t seconds, offset rows) covering one loop."""
    speed = REPEAT / LOOP
    dino_l, dino_r = DINO_COL, DINO_COL + DINO_W

    # fraction of a parabola of height JUMP_ROWS that sits above CACTUS_H
    frac = math.sqrt(1 - CACTUS_H / JUMP_ROWS)

    keys, SAMPLES = [(0.0, 0.0)], 13
    for col, art in obstacles():
        enter = (col - dino_r) / speed          # cactus reaches dino's right
        leave = (col + len(art[0]) - dino_l) / speed   # clears dino's left
        if leave < 0 or enter > LOOP:
            continue
        need = leave - enter
        air = need / frac * MARGIN
        mid = (enter + leave) / 2
        for i in range(SAMPLES + 1):
            u = i / SAMPLES
            keys.append((mid - air / 2 + u * air,
                         -JUMP_ROWS * (1 - (2 * u - 1) ** 2)))
    keys.append((LOOP, 0.0))
    keys.sort(key=lambda k: k[0])
    return keys


def build():
    rnd = random.Random(7)
    keys = jump_keys()

    seen, frames = set(), []
    for t, v in keys:
        pct = round(max(0.0, min(100.0, t / LOOP * 100)), 2)
        if pct in seen:
            continue
        seen.add(pct)
        frames.append(f"{pct}%{{transform:translateY({v * CH:.2f}px)}}")
    jump_kf = "".join(frames)

    stars = [(rnd.randrange(0, REPEAT * 2), rnd.randrange(0, GROUND_ROW - 4),
              rnd.choice([".", ".", "·", "*"])) for _ in range(90)]
    star_txt = "\n".join(
        f'<text x="{c * CW:.1f}" y="{(r + 1) * CH - 3:.1f}" '
        f'fill="{STAR}">{ch}</text>' for c, r, ch in stars)

    row = "".join("▂" if rnd.random() < .07 else
                  ("_" if rnd.random() < .72 else " ")
                  for _ in range(REPEAT * 2))
    ground = (f'<text x="0" y="{(GROUND_ROW + 1) * CH - 3:.1f}" '
              f'fill="{DIM}">{esc(row)}</text>')

    cacti_txt = "\n".join(
        sprite(art, col, GROUND_ROW - len(art), FG)
        for col, art in obstacles())

    top = GROUND_ROW - DINO_H
    body = sprite(DINO_BODY, DINO_COL, top, FG)
    la = sprite(LEGS_A, DINO_COL, top + len(DINO_BODY), FG, "la")
    lb = sprite(LEGS_B, DINO_COL, top + len(DINO_BODY), FG, "lb")

    w, h = COLS * CW, ROWS * CH
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" width="{DISPLAY_W}" height="{DISPLAY_W * h / w:.1f}" role="img" aria-label="ASCII dino runner">
<style>
text{{font-family:{FONT};font-size:{CH * .86:.1f}px;white-space:pre}}
.scroll{{animation:roll {LOOP}s linear infinite}}
@keyframes roll{{from{{transform:translateX(0)}}to{{transform:translateX(-{REPEAT * CW:.1f}px)}}}}
.stars{{animation:roll {LOOP * 4}s linear infinite}}
#dino{{animation:jump {LOOP}s linear infinite}}
@keyframes jump{{{jump_kf}}}
.la{{animation:st .3s steps(1,end) infinite}}
.lb{{animation:st .3s steps(1,end) infinite;animation-delay:.15s}}
@keyframes st{{0%,50%{{opacity:1}}50.01%,100%{{opacity:0}}}}
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
{la}
{lb}
</g>
</svg>'''


def check(steps=20000):
    """Re-simulate the emitted keyframes; fail loudly on any clipped cactus."""
    keys = jump_keys()
    speed = REPEAT / LOOP
    dino_l, dino_r = DINO_COL, DINO_COL + DINO_W

    def offset(t):
        for i in range(len(keys) - 1):
            (t0, v0), (t1, v1) = keys[i], keys[i + 1]
            if t0 <= t <= t1:
                f = 0 if t1 == t0 else (t - t0) / (t1 - t0)
                return v0 + f * (v1 - v0)
        return 0.0

    worst, hits = 99.0, 0
    for s in range(steps):
        t = s * LOOP / steps
        feet = GROUND_ROW + offset(t)
        for col, art in obstacles():
            x = col - speed * t
            if x + len(art[0]) > dino_l and x < dino_r:
                gap = (GROUND_ROW - len(art)) - feet
                worst = min(worst, gap)
                hits += gap < 0
    return worst, hits


if __name__ == "__main__":
    svg = build()
    with open("dino.svg", "w") as f:
        f.write(svg)
    worst, hits = check()
    print(f"dino.svg {len(svg)} bytes")
    print(f"min clearance over cactus: {worst:.2f} rows")
    print(f"collisions: {hits}")
    assert hits == 0, "dino clips a cactus"
