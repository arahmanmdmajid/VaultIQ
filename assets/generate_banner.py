"""
Generate team_banner.png for Nexus Warden / VaultIQ
Uses only Pillow — no system libraries required.
"""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1200, 630
OUT  = Path(__file__).parent / "team_banner.png"

# ── Colour palette ────────────────────────────────────────────────────────────
BG_DARK   = (3,   8,  16)
BG_MID    = (12,  37,  64)
CYAN      = (0,  200, 255)
GREEN     = (0,  255, 136)
WHITE     = (255, 255, 255)
ICE_BLUE  = (157, 216, 240)
DIM_CYAN  = (74, 138, 170)
PANEL_BG  = (10,  30,  48)

def hex_pts(cx, cy, r, angle_offset=90):
    """Return 6 (x,y) vertices for a pointy-top regular hexagon."""
    pts = []
    for i in range(6):
        a = math.radians(angle_offset + 60 * i)
        pts.append((cx + r * math.cos(a), cy - r * math.sin(a)))
    return pts

def glow_circle(img, cx, cy, r, colour, layers=6):
    """Draw a glowing dot by layering circles of decreasing opacity."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for i in range(layers, 0, -1):
        alpha = int(180 * (i / layers) ** 2)
        rad   = r + (layers - i) * 3
        d.ellipse(
            [cx - rad, cy - rad, cx + rad, cy + rad],
            fill=(*colour, alpha)
        )
    img.alpha_composite(overlay)

def glow_line(img, x0, y0, x1, y1, colour, width=2, alpha=140):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for w in range(width + 4, width - 1, -1):
        a = int(alpha * (w / (width + 4)) ** 2)
        d.line([(x0, y0), (x1, y1)], fill=(*colour, a), width=w)
    img.alpha_composite(overlay)

def glow_polygon(img, pts, colour, line_width=2, fill_alpha=12):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    if fill_alpha:
        d.polygon(pts, fill=(*colour, fill_alpha))
    for w in range(line_width + 3, line_width - 1, -1):
        a = int(180 * (w / (line_width + 3)) ** 2)
        d.polygon(pts, outline=(*colour, a))
    img.alpha_composite(overlay)

# ── Build image ───────────────────────────────────────────────────────────────
img = Image.new("RGBA", (W, H), BG_DARK)
draw = ImageDraw.Draw(img)

# 1. Radial background glow (centre of emblem ~300px from top)
for radius in range(360, 0, -4):
    alpha = int(55 * (1 - radius / 360) ** 1.6)
    x0, y0 = W // 2 - radius, 215 - radius
    x1, y1 = W // 2 + radius, 215 + radius
    draw.ellipse([x0, y0, x1, y1], fill=(*BG_MID, alpha))

# 2. Dot grid
for gx in range(0, W, 40):
    for gy in range(0, H, 40):
        draw.ellipse([gx + 19, gy + 19, gx + 21, gy + 21],
                     fill=(30, 74, 96, 100))

# 3. Background particles
particles = [
    (100, 75, 2, CYAN), (170, 210, 1, CYAN), (85, 380, 2, CYAN),
    (330, 45, 2, CYAN), (870, 38, 2, GREEN), (1070, 95, 2, GREEN),
    (1120, 290, 2, CYAN), (1035, 440, 2, GREEN), (210, 500, 2, GREEN),
    (960, 592, 1, CYAN), (260, 592, 2, GREEN), (410, 610, 1, CYAN),
    (795, 610, 2, GREEN),
]
for px, py, pr, pc in particles:
    glow_circle(img, px, py, pr, pc, layers=4)

# ── EMBLEM (cx=600, cy=215) ──────────────────────────────────────────────────
ECX, ECY = 600, 215

# Satellite node positions (radius 155, pointy-top hex pattern)
sat_nodes = hex_pts(ECX, ECY, 155, angle_offset=90)

# Outer satellite hexagon (connecting all 6 nodes, dim)
ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
dv = ImageDraw.Draw(ov)
dv.polygon(sat_nodes, outline=(*CYAN, 50))
img.alpha_composite(ov)

# Orbit ring (dashed circle)
for angle_deg in range(0, 360, 9):
    if (angle_deg // 9) % 3 != 2:
        a0 = math.radians(angle_deg)
        a1 = math.radians(angle_deg + 7)
        x0 = int(ECX + 155 * math.cos(a0))
        y0 = int(ECY - 155 * math.sin(a0))
        x1 = int(ECX + 155 * math.cos(a1))
        y1 = int(ECY - 155 * math.sin(a1))
        draw.line([(x0, y0), (x1, y1)], fill=(*DIM_CYAN, 110), width=1)

# Central hex vertices (radius 90)
hex_outer = hex_pts(ECX, ECY, 90)
hex_inner = hex_pts(ECX, ECY, 55)

# Spokes: central-hex vertex → satellite node
for (sv_x, sv_y), (nv_x, nv_y) in zip(hex_outer, sat_nodes):
    glow_line(img, int(sv_x), int(sv_y), int(nv_x), int(nv_y),
              CYAN, width=2, alpha=130)

# Satellite nodes
node_colours = [CYAN, CYAN, GREEN, CYAN, GREEN, CYAN]
for (nx, ny), nc in zip(sat_nodes, node_colours):
    glow_circle(img, int(nx), int(ny), 7, nc, layers=8)

# Central outer hexagon
glow_polygon(img, [(int(x), int(y)) for x, y in hex_outer],
             CYAN, line_width=3, fill_alpha=10)

# Central inner hexagon (dark filled)
inner_pts = [(int(x), int(y)) for x, y in hex_inner]
oi = Image.new("RGBA", img.size, (0, 0, 0, 0))
di = ImageDraw.Draw(oi)
di.polygon(inner_pts, fill=(5, 18, 40, 235))
img.alpha_composite(oi)
glow_polygon(img, inner_pts, CYAN, line_width=2, fill_alpha=0)

# Shield inside inner hex
shield_pts = [
    (ECX,       ECY - 55 + 15),   # top centre
    (ECX + 26,  ECY - 55 + 27),   # top right
    (ECX + 26,  ECY - 55 + 57),   # mid right
    (ECX + 18,  ECY - 55 + 73),   # lower right
    (ECX,       ECY - 55 + 82),   # bottom point
    (ECX - 18,  ECY - 55 + 73),   # lower left
    (ECX - 26,  ECY - 55 + 57),   # mid left
    (ECX - 26,  ECY - 55 + 27),   # top left
]
# shield_pts are relative to inner hex top; let's just use absolute coords:
shield_pts = [
    (ECX,       ECY - 40),
    (ECX + 26,  ECY - 28),
    (ECX + 26,  ECY + 2),
    (ECX + 18,  ECY + 18),
    (ECX,       ECY + 27),
    (ECX - 18,  ECY + 18),
    (ECX - 26,  ECY + 2),
    (ECX - 26,  ECY - 28),
]
glow_polygon(img, shield_pts, GREEN, line_width=2, fill_alpha=18)

# Centre nexus dot
glow_circle(img, ECX, ECY, 4, CYAN, layers=5)

# ── TEXT ─────────────────────────────────────────────────────────────────────
# Try to use a system bold font, fall back to default
def load_font(size, bold=False):
    candidates_bold = [
        "arialbd.ttf", "Arial_Bold.ttf", "DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/trebucbd.ttf",
    ]
    candidates_reg = [
        "arial.ttf", "DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/trebuc.ttf",
    ]
    for path in (candidates_bold if bold else candidates_reg):
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()

font_title    = load_font(80, bold=True)
font_tagline  = load_font(20)
font_sub      = load_font(15)
font_badge    = load_font(14, bold=True)
font_badge_sm = load_font(13)

def draw_text_centered(draw, img, text, y, font, colour, letter_spacing=0, glow=False):
    """Draw text centred at x=600 with optional glow and letter spacing."""
    if letter_spacing == 0:
        bbox  = draw.textbbox((0, 0), text, font=font)
        tw    = bbox[2] - bbox[0]
        x     = (W - tw) // 2
        if glow:
            glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow_layer)
            gd.text((x, y), text, font=font, fill=(*colour, 160))
            glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(10))
            img.alpha_composite(glow_layer)
        draw.text((x, y), text, font=font, fill=colour)
    else:
        # Manual letter spacing
        chars  = list(text)
        widths = [draw.textbbox((0, 0), c, font=font)[2] for c in chars]
        total  = sum(widths) + letter_spacing * (len(chars) - 1)
        x      = (W - total) // 2
        if glow:
            glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow_layer)
            xg = x
            for c, cw in zip(chars, widths):
                gd.text((xg, y), c, font=font, fill=(*colour, 150))
                xg += cw + letter_spacing
            glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(10))
            img.alpha_composite(glow_layer)
        xi = x
        for c, cw in zip(chars, widths):
            draw.text((xi, y), c, font=font, fill=colour)
            xi += cw + letter_spacing

# Title: gradient white → ice-blue via two-pass composite
draw_text_centered(draw, img, "NEXUS WARDEN", 400, font_title,
                   WHITE, letter_spacing=16, glow=True)

# Separator line
sep_y = 458
for xi in range(280, 920):
    t = (xi - 280) / 640
    if t < 0.15:
        alpha = int(220 * (t / 0.15))
    elif t > 0.85:
        alpha = int(220 * ((1 - t) / 0.15))
    else:
        alpha = 220
    colour_x = (
        int(0   + t * 0),
        int(200 + t * 55),
        int(255 - t * 119),
    )
    draw.point((xi, sep_y), fill=(*colour_x, alpha))

# Primary tagline
draw_text_centered(draw, img, "GOVERNED  DOCUMENT  INTELLIGENCE", sep_y + 22,
                   font_tagline, CYAN, letter_spacing=4)

# Secondary tagline
draw_text_centered(draw, img, "Connecting intelligence to action  ·  With governance at every layer",
                   sep_y + 50, font_sub, DIM_CYAN)

# VaultIQ badge
bx1, by1, bx2, by2 = 418, 535, 548, 565
draw.rounded_rectangle([bx1, by1, bx2, by2], radius=5,
                        fill=(13, 80, 112, 80), outline=(*DIM_CYAN, 200))
bbox_v = draw.textbbox((0, 0), "VaultIQ", font=font_badge)
tw_v   = bbox_v[2] - bbox_v[0]
draw.text(((bx1 + bx2 - tw_v) // 2, by1 + 8), "VaultIQ", font=font_badge, fill=CYAN)

# · divider
draw.ellipse([597, 547, 603, 553], fill=(*DIM_CYAN, 180))

# TechEx badge
bx3, by3, bx4, by4 = 618, 535, 800, 565
draw.rounded_rectangle([bx3, by3, bx4, by4], radius=5,
                        fill=(13, 60, 80, 60), outline=(13, 74, 94, 160))
bbox_t = draw.textbbox((0, 0), "TechEx Hackathon 2025", font=font_badge_sm)
tw_t   = bbox_t[2] - bbox_t[0]
draw.text(((bx3 + bx4 - tw_t) // 2, by3 + 9),
          "TechEx Hackathon 2025", font=font_badge_sm, fill=DIM_CYAN)

# ── FRAME ────────────────────────────────────────────────────────────────────
# Top & bottom accent bars (cyan→green gradient)
for xi in range(W):
    t = xi / W
    c = (int(0 + t * 0), int(200 + t * 55), int(255 - t * 119))
    draw.point((xi, 0),   fill=(*c, 200))
    draw.point((xi, 1),   fill=(*c, 160))
    draw.point((xi, 2),   fill=(*c, 80))
    draw.point((xi, H-1), fill=(*c, 200))
    draw.point((xi, H-2), fill=(*c, 160))
    draw.point((xi, H-3), fill=(*c, 80))

# Corner L-brackets
bracket_len, bracket_w = 44, 2
corners = [(0, 0, 1, 1), (W, 0, -1, 1), (0, H, 1, -1), (W, H, -1, -1)]
for cx2, cy2, dx, dy in corners:
    draw.line([(cx2, cy2), (cx2 + dx * bracket_len, cy2)],
              fill=(*CYAN, 160), width=bracket_w)
    draw.line([(cx2, cy2), (cx2, cy2 + dy * bracket_len)],
              fill=(*CYAN, 160), width=bracket_w)

# ── Save ─────────────────────────────────────────────────────────────────────
final = img.convert("RGB")
final.save(OUT, "PNG", optimize=True)
print(f"Saved: {OUT}  ({OUT.stat().st_size // 1024} KB)")
