import os
import math
from PIL import Image, ImageDraw

def create_svg():
    return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100%" height="100%">
  <defs>
    <!-- Obsidian Dark Background Gradient -->
    <linearGradient id="obsidianGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1e2638"/>
      <stop offset="45%" stop-color="#0f1523"/>
      <stop offset="100%" stop-color="#060911"/>
    </linearGradient>

    <!-- Bevel & Border Light Catcher -->
    <linearGradient id="bevelGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.5"/>
      <stop offset="50%" stop-color="#1e293b" stop-opacity="0.2"/>
      <stop offset="100%" stop-color="#10b981" stop-opacity="0.4"/>
    </linearGradient>

    <!-- Luminous Navigation Aperture Gradient (Cobalt to Emerald) -->
    <linearGradient id="apertureGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8"/>
      <stop offset="35%" stop-color="#2563eb"/>
      <stop offset="70%" stop-color="#00f5a0"/>
      <stop offset="100%" stop-color="#10b981"/>
    </linearGradient>

    <!-- Compass Needle North (Luminous Cobalt / Cyan) -->
    <linearGradient id="needleNorthLight" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ffffff"/>
      <stop offset="100%" stop-color="#38bdf8"/>
    </linearGradient>
    <linearGradient id="needleNorthDark" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8"/>
      <stop offset="100%" stop-color="#1d4ed8"/>
    </linearGradient>

    <!-- Compass Needle South (Luminous Emerald / Mint) -->
    <linearGradient id="needleSouthLight" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00f5a0"/>
      <stop offset="100%" stop-color="#10b981"/>
    </linearGradient>
    <linearGradient id="needleSouthDark" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#10b981"/>
      <stop offset="100%" stop-color="#047857"/>
    </linearGradient>

    <!-- Soft Glow Filter -->
    <filter id="softGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="8" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>

    <!-- Center Pulse Glow -->
    <filter id="centerGlow" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="6" result="blurCore"/>
      <feMerge>
        <feMergeNode in="blurCore"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- 1. Sleek Obsidian Squircle Container -->
  <rect x="28" y="28" width="456" height="456" rx="108" ry="108" fill="url(#obsidianGrad)" stroke="url(#bevelGrad)" stroke-width="3"/>

  <!-- 2. Subtle Navigation Aperture Well (Depth) -->
  <circle cx="256" cy="256" r="162" fill="#090d16" stroke="rgba(56, 189, 248, 0.15)" stroke-width="1.5"/>

  <!-- 3. Luminous Outer Aperture Track (Cobalt to Emerald) -->
  <circle cx="256" cy="256" r="142" fill="none" stroke="url(#apertureGrad)" stroke-width="14" stroke-linecap="round" filter="url(#softGlow)"/>

  <!-- 4. Concentric Geometry Calibration Rings (Minimalist Precision) -->
  <circle cx="256" cy="256" r="108" fill="none" stroke="#38bdf8" stroke-width="1.5" stroke-opacity="0.35"/>
  <circle cx="256" cy="256" r="76" fill="none" stroke="#00f5a0" stroke-width="1" stroke-opacity="0.25"/>

  <!-- 5. Refined Precision Navigation Pointer (Rotated 45° - North East / Exploration) -->
  <g transform="rotate(45 256 256)" filter="url(#softGlow)">
    <!-- North Pointer (Discovery / Sky / Cobalt) -->
    <polygon points="256,256 238,256 256,152" fill="url(#needleNorthLight)"/>
    <polygon points="256,256 274,256 256,152" fill="url(#needleNorthDark)"/>

    <!-- South Pointer (Grounding / Emerald / Mint) -->
    <polygon points="256,256 238,256 256,360" fill="url(#needleSouthLight)"/>
    <polygon points="256,256 274,256 256,360" fill="url(#needleSouthDark)"/>
  </g>

  <!-- 6. Central Luminous Core / Aperture Eye -->
  <g filter="url(#centerGlow)">
    <circle cx="256" cy="256" r="22" fill="#ffffff"/>
    <circle cx="256" cy="256" r="13" fill="#00f5a0"/>
    <circle cx="256" cy="256" r="6" fill="#ffffff"/>
  </g>
</svg>'''

def render_master_icon():
    # Render at 1024x1024 (2x supersampling for high fidelity downscaling)
    size = 1024
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    s = size / 512.0
    pad = int(28 * s)
    w = int(456 * s)
    radius = int(108 * s)

    # 1. Base Squircle (Obsidian)
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([pad, pad, pad + w, pad + w], radius=radius, fill=255)

    obsidian = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    obs_draw = ImageDraw.Draw(obsidian)
    for y in range(pad, pad + w):
        t = (y - pad) / float(w)
        # Gradient: #1e2638 (30, 38, 56) -> #0f1523 (15, 21, 35) -> #060911 (6, 9, 17)
        if t < 0.5:
            st = t / 0.5
            r = int(30 * (1 - st) + 15 * st)
            g = int(38 * (1 - st) + 21 * st)
            b = int(56 * (1 - st) + 35 * st)
        else:
            st = (t - 0.5) / 0.5
            r = int(15 * (1 - st) + 6 * st)
            g = int(21 * (1 - st) + 9 * st)
            b = int(35 * (1 - st) + 17 * st)
        obs_draw.line([(pad, y), (pad + w, y)], fill=(r, g, b, 255))

    img.paste(obsidian, (0, 0), mask)

    # Bevel border
    draw.rounded_rectangle([pad, pad, pad + w, pad + w], radius=radius, outline=(56, 189, 248, 120), width=max(2, int(3 * s)))

    cx, cy = size / 2.0, size / 2.0

    # 2. Aperture Well
    r_well = int(162 * s)
    draw.ellipse([cx - r_well, cy - r_well, cx + r_well, cy + r_well], fill=(9, 13, 22, 255), outline=(56, 189, 248, 50), width=max(1, int(1.5 * s)))

    # 3. Luminous Aperture Ring (Cobalt to Emerald)
    r_ring = int(142 * s)
    ring_w = max(4, int(14 * s))
    steps = 180
    for i in range(steps):
        angle1 = math.radians(i * 2 - 90)
        angle2 = math.radians(i * 2 - 90 + 2.5)
        t = i / float(steps)
        if t < 0.35:
            st = t / 0.35
            cr = int(56 * (1 - st) + 37 * st)
            cg = int(189 * (1 - st) + 99 * st)
            cb = int(248 * (1 - st) + 235 * st)
        elif t < 0.7:
            st = (t - 0.35) / 0.35
            cr = int(37 * (1 - st) + 0 * st)
            cg = int(99 * (1 - st) + 245 * st)
            cb = int(235 * (1 - st) + 160 * st)
        else:
            st = (t - 0.7) / 0.30
            cr = int(0 * (1 - st) + 16 * st)
            cg = int(245 * (1 - st) + 185 * st)
            cb = int(160 * (1 - st) + 129 * st)

        p1 = (cx + (r_ring - ring_w/2) * math.cos(angle1), cy + (r_ring - ring_w/2) * math.sin(angle1))
        p2 = (cx + (r_ring + ring_w/2) * math.cos(angle1), cy + (r_ring + ring_w/2) * math.sin(angle1))
        p3 = (cx + (r_ring + ring_w/2) * math.cos(angle2), cy + (r_ring + ring_w/2) * math.sin(angle2))
        p4 = (cx + (r_ring - ring_w/2) * math.cos(angle2), cy + (r_ring - ring_w/2) * math.sin(angle2))
        draw.polygon([p1, p2, p3, p4], fill=(cr, cg, cb, 255))

    # 4. Concentric Geometry Calibration Rings
    r_track1 = int(108 * s)
    draw.ellipse([cx - r_track1, cy - r_track1, cx + r_track1, cy + r_track1], outline=(56, 189, 248, 90), width=max(1, int(1.5 * s)))
    r_track2 = int(76 * s)
    draw.ellipse([cx - r_track2, cy - r_track2, cx + r_track2, cy + r_track2], outline=(0, 245, 160, 70), width=max(1, int(1 * s)))

    # 5. Faceted Navigation Compass Pointer (45° rotation)
    rot = -math.pi / 4.0
    def rot_pt(x, y):
        rx = x * math.cos(rot) - y * math.sin(rot)
        ry = x * math.sin(rot) + y * math.cos(rot)
        return (cx + rx, cy + ry)

    top_d = 104 * s
    bot_d = 104 * s
    side_w = 18 * s

    p_center = rot_pt(0, 0)
    p_top = rot_pt(0, -top_d)
    p_bot = rot_pt(0, bot_d)
    p_left = rot_pt(-side_w, 0)
    p_right = rot_pt(side_w, 0)

    # North pointer (Luminous Cyan / Cobalt)
    draw.polygon([p_center, p_left, p_top], fill=(255, 255, 255, 250))
    draw.polygon([p_center, p_right, p_top], fill=(56, 189, 248, 250))

    # South pointer (Mint / Emerald)
    draw.polygon([p_center, p_left, p_bot], fill=(0, 245, 160, 250))
    draw.polygon([p_center, p_right, p_bot], fill=(16, 185, 129, 240))

    # 6. Central Luminous Core
    r_hub = max(3, int(22 * s))
    draw.ellipse([cx - r_hub, cy - r_hub, cx + r_hub, cy + r_hub], fill=(255, 255, 255, 255))
    r_hub_in = max(2, int(13 * s))
    draw.ellipse([cx - r_hub_in, cy - r_hub_in, cx + r_hub_in, cy + r_hub_in], fill=(0, 245, 160, 255))
    r_hub_dot = max(1, int(6 * s))
    draw.ellipse([cx - r_hub_dot, cy - r_hub_dot, cx + r_hub_dot, cy + r_hub_dot], fill=(255, 255, 255, 255))

    return img

if __name__ == '__main__':
    os.makedirs('browser/ui', exist_ok=True)
    os.makedirs('browser/Chromium-win32-x64', exist_ok=True)
    os.makedirs('IDE', exist_ok=True)

    # 1. Write SVG
    svg = create_svg()
    with open('browser/ui/favicon.svg', 'w', encoding='utf-8') as f:
        f.write(svg)
    print("[OK] Created browser/ui/favicon.svg")

    # 2. Render Master Icon
    master = render_master_icon()

    # 3. Save PNG sizes
    img_512 = master.resize((512, 512), Image.Resampling.LANCZOS)
    img_512.save('browser/ui/icon-512.png', format='PNG')
    print("[OK] Created browser/ui/icon-512.png")

    img_192 = master.resize((192, 192), Image.Resampling.LANCZOS)
    img_192.save('browser/ui/icon-192.png', format='PNG')
    print("[OK] Created browser/ui/icon-192.png")

    img_32 = master.resize((32, 32), Image.Resampling.LANCZOS)
    img_32.save('browser/ui/favicon-32x32.png', format='PNG')
    print("[OK] Created browser/ui/favicon-32x32.png")

    img_16 = master.resize((16, 16), Image.Resampling.LANCZOS)
    img_16.save('browser/ui/favicon-16x16.png', format='PNG')
    print("[OK] Created browser/ui/favicon-16x16.png")

    # 4. Multi-Resolution Windows ICO
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    ico_images = [master.resize(s, Image.Resampling.LANCZOS) for s in sizes]

    ico_images[0].save('browser/ui/favicon.ico', format='ICO', sizes=sizes)
    print("[OK] Created browser/ui/favicon.ico")

    ico_images[0].save('browser/ui/hugos_browser.ico', format='ICO', sizes=sizes)
    ico_images[0].save('browser/Chromium-win32-x64/hugos_browser.ico', format='ICO', sizes=sizes)
    ico_images[0].save('IDE/hugos_browser.ico', format='ICO', sizes=sizes)
    print("[OK] Created hugos_browser.ico across browser and IDE packaging locations.")
