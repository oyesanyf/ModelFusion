import os
import math
from PIL import Image, ImageDraw

def create_svg():
    svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100%" height="100%">
  <defs>
    <!-- Background Gradient -->
    <radialGradient id="bgGrad" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#1e293b"/>
      <stop offset="60%" stop-color="#0f172a"/>
      <stop offset="100%" stop-color="#070b14"/>
    </radialGradient>

    <!-- Emerald / Cyan Fusion Ring Gradient -->
    <linearGradient id="ringGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00f5a0"/>
      <stop offset="50%" stop-color="#00d9f5"/>
      <stop offset="100%" stop-color="#3b82f6"/>
    </linearGradient>

    <!-- Core Star Gradient -->
    <linearGradient id="coreGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ffffff"/>
      <stop offset="35%" stop-color="#a7f3d0"/>
      <stop offset="70%" stop-color="#06b6d4"/>
      <stop offset="100%" stop-color="#10b981"/>
    </linearGradient>

    <!-- Glow Filter -->
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="12" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    
    <filter id="coreGlow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="18" result="blur2"/>
      <feMerge>
        <feMergeNode in="blur2"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- Base Circle with dark depth -->
  <circle cx="256" cy="256" r="240" fill="url(#bgGrad)" stroke="#334155" stroke-width="4"/>

  <!-- Subtle Outer Energy Pulse -->
  <circle cx="256" cy="256" r="226" fill="none" stroke="url(#ringGrad)" stroke-width="3" stroke-opacity="0.3" stroke-dasharray="16 8"/>

  <!-- Main Cyber Orbital Ring (Browser Aperture) -->
  <circle cx="256" cy="256" r="195" fill="none" stroke="url(#ringGrad)" stroke-width="18" stroke-linecap="round" stroke-dasharray="280 40 180 30" filter="url(#glow)"/>

  <!-- Inner Concentric Tech Track -->
  <circle cx="256" cy="256" r="150" fill="none" stroke="#00f5a0" stroke-width="4" stroke-opacity="0.4" stroke-dasharray="8 12"/>

  <!-- Secondary Tilted Orbital Loop (Multi-Modal Dimension) -->
  <ellipse cx="256" cy="256" rx="180" ry="85" fill="none" stroke="url(#ringGrad)" stroke-width="8" transform="rotate(-30 256 256)" stroke-opacity="0.85" filter="url(#glow)"/>

  <!-- Satellite Nodes (Vision, Audio, Web, Reasoning) -->
  <circle cx="110" cy="170" r="14" fill="#00f5a0" filter="url(#glow)"/>
  <circle cx="402" cy="342" r="14" fill="#00d9f5" filter="url(#glow)"/>
  <circle cx="340" cy="120" r="10" fill="#38bdf8" filter="url(#glow)"/>
  <circle cx="172" cy="392" r="10" fill="#10b981" filter="url(#glow)"/>

  <!-- Center Intelligence Core - Multi-Ray AI Fusion Star -->
  <g filter="url(#coreGlow)">
    <!-- 4-point Diamond Starburst -->
    <path d="M 256 95 Q 256 256 95 256 Q 256 256 256 417 Q 256 256 417 256 Q 256 256 256 95 Z" fill="url(#coreGrad)"/>
    
    <!-- 45-degree Inner Star -->
    <path d="M 256 160 Q 256 256 160 256 Q 256 256 256 352 Q 256 256 352 256 Q 256 256 256 160 Z" fill="#ffffff" opacity="0.9"/>

    <!-- Central Fusion Core Pulse -->
    <circle cx="256" cy="256" r="28" fill="#ffffff"/>
    <circle cx="256" cy="256" r="16" fill="#00f5a0"/>
  </g>
</svg>'''
    return svg_content

def render_png(size=512):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    scale = size / 512.0
    cx, cy = size / 2.0, size / 2.0
    r = int(240 * scale)
    
    # Outer background
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(15, 23, 42, 255), outline=(51, 65, 85, 255), width=max(1, int(4 * scale)))
    
    # Main ring
    r_ring = int(195 * scale)
    ring_width = max(2, int(18 * scale))
    draw.ellipse([cx - r_ring, cy - r_ring, cx + r_ring, cy + r_ring], outline=(0, 245, 160, 255), width=ring_width)
    
    # Tilted ellipse
    bbox = [cx - int(180 * scale), cy - int(85 * scale), cx + int(180 * scale), cy + int(85 * scale)]
    draw.ellipse(bbox, outline=(0, 217, 245, 220), width=max(1, int(8 * scale)))
    
    # Satellite Nodes
    def draw_node(x, y, rad, color):
        nx, ny = int(x * scale), int(y * scale)
        nrad = max(2, int(rad * scale))
        draw.ellipse([nx - nrad, ny - nrad, nx + nrad, ny + nrad], fill=color)

    draw_node(110, 170, 14, (0, 245, 160, 255))
    draw_node(402, 342, 14, (0, 217, 245, 255))
    draw_node(340, 120, 10, (56, 189, 248, 255))
    draw_node(172, 392, 10, (16, 185, 129, 255))
    
    # Center 4-point star
    star_pts = []
    num_steps = 32
    for i in range(num_steps * 4):
        theta = i * 2 * math.pi / (num_steps * 4)
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        d = (abs(cos_t)**0.5 + abs(sin_t)**0.5)**2
        rad_star = (140 * scale) / max(0.001, d)
        px = cx + rad_star * cos_t
        py = cy + rad_star * sin_t
        star_pts.append((px, py))
    
    draw.polygon(star_pts, fill=(0, 245, 160, 255))
    
    # Inner bright star
    inner_pts = []
    for i in range(num_steps * 4):
        theta = i * 2 * math.pi / (num_steps * 4)
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        d = (abs(cos_t)**0.5 + abs(sin_t)**0.5)**2
        rad_star = (80 * scale) / max(0.001, d)
        px = cx + rad_star * cos_t
        py = cy + rad_star * sin_t
        inner_pts.append((px, py))
    draw.polygon(inner_pts, fill=(255, 255, 255, 240))

    # Center circle
    c_r = max(2, int(22 * scale))
    draw.ellipse([cx - c_r, cy - c_r, cx + c_r, cy + c_r], fill=(255, 255, 255, 255))
    c_inner = max(1, int(12 * scale))
    draw.ellipse([cx - c_inner, cy - c_inner, cx + c_inner, cy + c_inner], fill=(0, 245, 160, 255))
    
    return img

if __name__ == '__main__':
    os.makedirs('browser/ui', exist_ok=True)
    os.makedirs('browser/Chromium-win32-x64', exist_ok=True)
    os.makedirs('IDE', exist_ok=True)

    # 1. Write SVG
    svg = create_svg()
    with open('browser/ui/favicon.svg', 'w', encoding='utf-8') as f:
        f.write(svg)
    print("Created browser/ui/favicon.svg")

    # 2. Render PNGs
    img_512 = render_png(512)
    img_512.save('browser/ui/icon-512.png', format='PNG')
    print("Created browser/ui/icon-512.png")

    img_192 = render_png(192)
    img_192.save('browser/ui/icon-192.png', format='PNG')
    print("Created browser/ui/icon-192.png")

    img_32 = render_png(32)
    img_32.save('browser/ui/favicon-32x32.png', format='PNG')
    print("Created browser/ui/favicon-32x32.png")

    img_16 = render_png(16)
    img_16.save('browser/ui/favicon-16x16.png', format='PNG')
    print("Created browser/ui/favicon-16x16.png")

    # 3. Create Windows Multi-Resolution ICO files
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    ico_images = [render_png(s[0]) for s in sizes]
    
    ico_images[0].save('browser/ui/favicon.ico', format='ICO', sizes=sizes)
    print("Created browser/ui/favicon.ico")

    ico_images[0].save('browser/ui/hugos_browser.ico', format='ICO', sizes=sizes)
    ico_images[0].save('browser/Chromium-win32-x64/hugos_browser.ico', format='ICO', sizes=sizes)
    ico_images[0].save('IDE/hugos_browser.ico', format='ICO', sizes=sizes)
    print("Created hugos_browser.ico across browser and IDE directories.")
