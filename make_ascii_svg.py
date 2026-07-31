#!/usr/bin/env python3
"""
Generate animated ASCII-art SVGs for a GitHub profile README.

Two generators:
  ascii_image_svg() - converts a raster image to ASCII and reveals it row by row
  wordmark_svg()    - renders text as 3D block ASCII that wipes in left to right

Animation is plain CSS inside the SVG, which still runs when GitHub renders the
file via <img src="./name.svg">. No GIFs, no external requests.
"""

from PIL import Image, ImageOps
import html

CH_W = 6.021        # advance width of the monospace face at 10px
CH_H = 11.0         # line height
FONT_PX = 10
FONT = ("ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,"
        "'Liberation Mono',monospace")

RAMP = " .,:;i1tfLCG08@"   # dark -> light


def _tint(v, palette):
    """Pick a palette colour for a 0..255 luminance value."""
    idx = min(len(palette) - 1, int(v / 256 * len(palette)))
    return palette[idx]


def ascii_image_svg(src, out, cols=104, palette=None, bg="#0d1117",
                    reveal=2.6, gamma=1.0, invert=False, cursor=True,
                    equalize=False, autocontrast=None):
    palette = palette or ["#0b2545", "#12386b", "#1d5a9e", "#2f81f7",
                          "#58a6ff", "#9ecbff", "#d6e9ff"]

    im = Image.open(src).convert("L")
    # Source images are low-contrast; spread the histogram or the ramp collapses
    # into two or three characters and the subject stops being legible.
    if equalize:
        im = ImageOps.equalize(im)
    elif autocontrast is not None:
        im = ImageOps.autocontrast(im, cutoff=autocontrast)
    if invert:
        im = ImageOps.invert(im)
    w, h = im.size
    rows = max(1, int(cols * (h / w) * (CH_W / CH_H)))
    im = im.resize((cols, rows), Image.LANCZOS)
    px = im.load()

    width = cols * CH_W
    height = rows * CH_H + (CH_H if cursor else 0)

    out_rows = []
    for y in range(rows):
        # group consecutive characters that share a colour bucket into one tspan
        runs, cur_col, cur_txt = [], None, []
        for x in range(cols):
            v = px[x, y]
            if gamma != 1.0:
                v = int(255 * ((v / 255) ** gamma))
            ch = RAMP[min(len(RAMP) - 1, int(v / 256 * len(RAMP)))]
            col = _tint(v, palette)
            if col != cur_col:
                if cur_txt:
                    runs.append((cur_col, "".join(cur_txt)))
                cur_col, cur_txt = col, [ch]
            else:
                cur_txt.append(ch)
        if cur_txt:
            runs.append((cur_col, "".join(cur_txt)))

        spans = "".join(
            f'<tspan fill="{c}">{html.escape(t)}</tspan>' for c, t in runs
        )
        delay = round(reveal * (y / max(1, rows - 1)), 3)
        out_rows.append(
            f'<text class="r" style="animation-delay:{delay}s" '
            f'x="0" y="{round((y + 1) * CH_H - 2, 2)}">{spans}</text>'
        )

    cur = ""
    if cursor:
        cur = (f'<rect class="cur" x="0" y="{round(rows * CH_H - 6, 2)}" '
               f'width="{round(CH_W, 2)}" height="9" fill="#58a6ff"/>')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {round(width,2)} {round(height,2)}" width="{round(width,2)}" height="{round(height,2)}" role="img" aria-label="ASCII art">
<style>
text{{font-family:{FONT};font-size:{FONT_PX}px;white-space:pre;dominant-baseline:auto}}
.r{{opacity:0;animation:in .28s steps(1,end) forwards}}
@keyframes in{{to{{opacity:1}}}}
.cur{{animation:blink 1.06s steps(1,end) infinite;animation-delay:{reveal}s;opacity:0}}
@keyframes blink{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}
@media(prefers-reduced-motion:reduce){{.r{{opacity:1;animation:none}}.cur{{animation:none;opacity:1}}}}
</style>
<rect width="100%" height="100%" fill="{bg}"/>
{chr(10).join(out_rows)}
{cur}
</svg>'''
    with open(out, "w") as f:
        f.write(svg)
    return out, cols, rows, len(svg)


# ---------------------------------------------------------------- wordmark ---

GLYPHS = {
    "A": [" ##### ", "##   ##", "##   ##", "#######", "##   ##", "##   ##", "##   ##"],
    "B": ["###### ", "##   ##", "##   ##", "###### ", "##   ##", "##   ##", "###### "],
    "I": ["#######", "  ###  ", "  ###  ", "  ###  ", "  ###  ", "  ###  ", "#######"],
    "L": ["##     ", "##     ", "##     ", "##     ", "##     ", "##     ", "#######"],
    "R": ["###### ", "##   ##", "##   ##", "###### ", "##  ## ", "##   ##", "##   ##"],
    "S": [" ######", "##     ", "##     ", " ##### ", "     ##", "     ##", "###### "],
    " ": ["   ", "   ", "   ", "   ", "   ", "   ", "   "],
}


def wordmark_svg(text, out, face="#58a6ff", depth="#1f4f87", bg="#0d1117",
                 scale=2, dur=1.5):
    text = text.upper()
    rows = 7
    grid = ["" for _ in range(rows)]
    for chx in text:
        g = GLYPHS.get(chx, GLYPHS[" "])
        for r in range(rows):
            grid[r] += g[r] + " "

    cols = max(len(r) for r in grid)
    grid = [r.ljust(cols) for r in grid]

    cw, chh = CH_W * scale, CH_H * scale
    # +1 char of headroom for the extruded shadow layer
    width = (cols + 1) * cw
    height = (rows + 1) * chh

    def layer(dx, dy, fill, cls):
        parts = []
        for y, line in enumerate(grid):
            if not line.strip():
                continue
            parts.append(
                f'<text class="{cls}" x="{round(dx,2)}" '
                f'y="{round((y + 1) * chh + dy, 2)}" fill="{fill}">'
                f'{html.escape(line.replace("#", "█"))}</text>'
            )
        return "\n".join(parts)

    shadow = layer(cw * 0.45, chh * 0.30, depth, "l")
    front = layer(0, 0, face, "l")

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {round(width,2)} {round(height,2)}" width="{round(width,2)}" height="{round(height,2)}" role="img" aria-label="{html.escape(text)}">
<style>
text{{font-family:{FONT};font-size:{round(FONT_PX*scale,2)}px;white-space:pre}}
#wipe rect{{transform-origin:0 0;transform:scaleX(0);animation:wipe {dur}s cubic-bezier(.22,1,.36,1) forwards}}
@keyframes wipe{{to{{transform:scaleX(1)}}}}
#g{{animation:rock 6s ease-in-out {dur}s infinite}}
@keyframes rock{{0%,100%{{transform:skewX(0deg)}}50%{{transform:skewX(-3.5deg)}}}}
@media(prefers-reduced-motion:reduce){{#wipe rect{{transform:scaleX(1);animation:none}}#g{{animation:none}}}}
</style>
<rect width="100%" height="100%" fill="{bg}"/>
<clipPath id="wipe"><rect width="{round(width,2)}" height="{round(height,2)}"/></clipPath>
<g clip-path="url(#wipe)"><g id="g" style="transform-origin:50% 50%">
{shadow}
{front}
</g></g>
</svg>'''
    with open(out, "w") as f:
        f.write(svg)
    return out, cols, rows, len(svg)


if __name__ == "__main__":
    print(ascii_image_svg("banner.jpeg", "hero.svg", cols=104,
                          equalize=True, gamma=1.25, reveal=2.4))
    print(wordmark_svg("ALI SIRBALI", "wordmark.svg", scale=2))
    print(ascii_image_svg(
        "footer.jpeg", "dino.svg", cols=150, autocontrast=1, gamma=1.1,
        reveal=1.8, cursor=False,
        palette=["#0d1117", "#1c2530", "#2d3743", "#556170",
                 "#8b98a6", "#c9d1d9", "#ffffff"]))
