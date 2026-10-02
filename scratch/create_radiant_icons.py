import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import shutil

def generate_radiant_suite():
    # 1. Load the original IDE icon as source
    src_path = r'd:\harfile\ModelFusion\IDE\hugos_1024x1024.png'
    if not os.path.exists(src_path):
        print(f"Error: {src_path} not found")
        return

    src_img = Image.open(src_path).convert('RGBA')
    src_arr = np.array(src_img)

    # 2. Extract the brain intensity mask
    # Background in original is dark navy [7, 14, 32]
    # Bright pixels are circuit lines/nodes
    bg_color = np.array([7.0, 14.0, 32.0])
    diff = src_arr[:, :, :3].astype(float) - bg_color
    intensity = np.clip((diff[:, :, 1] * 1.5 + diff[:, :, 2] * 1.2 + diff[:, :, 0] * 0.5) / 180.0, 0.0, 1.0)
    
    # Clean threshold and boost contrast
    intensity[intensity < 0.12] = 0.0
    intensity = np.power(intensity, 0.82)

    # Isolate the brain portion (Y: 140 to 680)
    brain_mask = np.copy(intensity)
    brain_mask[680:, :] = 0.0
    brain_mask[:140, :] = 0.0

    print(f"Brain mask max intensity: {brain_mask.max()}, non-zero count: {np.count_nonzero(brain_mask > 0.1)}")

    # 3. Define the Gemini-inspired vibrant color palette
    # Transitions smoothly from:
    # Top-Left: Vivid Scarlet Red (#FF1A4B) -> Fiery Coral (#FF6B35) -> Radiant Orchid/Magenta (#E81E99)
    # Center-Right: Electric Violet (#8B2FE8) -> Luminous Cyan / Azure (#00E5FF) -> Aquamarine (#00FFB2)
    H, W = 1024, 1024
    y_coords, x_coords = np.mgrid[0:H, 0:W]
    cx, cy = 512.0, 415.0
    
    # Angle progression from top-left to bottom-right
    proj = ((x_coords - cx) * 0.85 + (y_coords - cy) * 0.53) / 280.0
    t = np.clip((proj + 1.1) / 2.2, 0.0, 1.0)

    color_stops = [
        (0.00, np.array([255, 26, 75])),    # Vivid Scarlet Red (#FF1A4B)
        (0.20, np.array([255, 107, 53])),   # Fiery Coral (#FF6B35)
        (0.40, np.array([238, 30, 153])),   # Radiant Magenta / Orchid (#EE1E99)
        (0.60, np.array([145, 47, 235])),   # Deep Electric Violet (#912FEB)
        (0.80, np.array([0, 225, 255])),    # Electric Azure / Cyan (#00E1FF)
        (1.00, np.array([0, 255, 185]))     # Luminous Aquamarine (#00FFB9)
    ]

    gradient_rgb = np.zeros((H, W, 3), dtype=float)
    for i in range(len(color_stops) - 1):
        t0, c0 = color_stops[i]
        t1, c1 = color_stops[i+1]
        weight = np.clip((t - t0) / (t1 - t0), 0.0, 1.0)
        idx_mask = (t >= t0) & (t <= t1)
        gradient_rgb[idx_mask] = (c0 * (1.0 - weight[idx_mask, None]) + c1 * weight[idx_mask, None])

    # Core brain color = gradient * intensity + white synapse highlight boost
    brain_rgb = np.zeros((H, W, 3), dtype=np.uint8)
    brain_alpha = (brain_mask * 255).astype(np.uint8)
    
    highlight = np.clip((brain_mask - 0.65) / 0.35, 0.0, 1.0)
    for c in range(3):
        channel = gradient_rgb[:, :, c] * brain_mask + 255.0 * highlight * 0.55
        brain_rgb[:, :, c] = np.clip(channel, 0, 255).astype(np.uint8)

    # Function to build an icon with squircle, ambient glow, neural brain, and badge text
    def build_icon(app_title, is_browser=False):
        icon_img = Image.new('RGBA', (1024, 1024), (0, 0, 0, 0))

        # Squircle padding = 44px
        pad = 44
        r = 210
        box = [pad, pad, 1024 - pad, 1024 - pad]
        
        # Outer ambient glow / soft shadow
        glow_canvas = Image.new('RGBA', (1024, 1024), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_canvas)
        glow_draw.rounded_rectangle(box, radius=r, fill=(25, 15, 45, 190))
        glow_canvas = glow_canvas.filter(ImageFilter.GaussianBlur(18))
        icon_img.alpha_composite(glow_canvas)

        # Dark obsidian base squircle (#070b14 -> #0f172a gradient)
        squircle_mask = Image.new('L', (1024, 1024), 0)
        s_draw = ImageDraw.Draw(squircle_mask)
        s_draw.rounded_rectangle(box, radius=r, fill=255)

        sq_arr = np.zeros((1024, 1024, 4), dtype=np.uint8)
        for y in range(1024):
            frac = y / 1024.0
            r_val = int(8 + (1 - frac) * 8 + frac * 2)
            g_val = int(10 + frac * 10)
            b_val = int(22 + frac * 18)
            sq_arr[y, :, 0] = r_val
            sq_arr[y, :, 1] = g_val
            sq_arr[y, :, 2] = b_val
            sq_arr[y, :, 3] = 255
        sq_grad = Image.fromarray(sq_arr)
        icon_img.paste(sq_grad, (0, 0), squircle_mask)

        # Radiant multi-color Gemini border stroke (width=7)
        border_canvas = Image.new('RGBA', (1024, 1024), (0, 0, 0, 0))
        b_draw = ImageDraw.Draw(border_canvas)
        b_draw.rounded_rectangle(box, radius=r, outline=(255, 255, 255, 140), width=7)
        
        b_arr = np.array(border_canvas)
        b_mask = b_arr[:, :, 3] > 0
        for c in range(3):
            b_arr[b_mask, c] = gradient_rgb[b_mask, c].astype(np.uint8)
        border_colored = Image.fromarray(b_arr)
        icon_img.alpha_composite(border_colored)

        # Inner ambient brain glow
        bglow_arr = np.zeros((1024, 1024, 4), dtype=np.uint8)
        bglow_arr[:, :, :3] = brain_rgb
        bglow_arr[:, :, 3] = (brain_mask * 150).astype(np.uint8)
        brain_glow_img = Image.fromarray(bglow_arr).filter(ImageFilter.GaussianBlur(16))
        icon_img.alpha_composite(brain_glow_img)

        # Paste the sharp glowing brain
        bsharp_arr = np.zeros((1024, 1024, 4), dtype=np.uint8)
        bsharp_arr[:, :, :3] = brain_rgb
        bsharp_arr[:, :, 3] = brain_alpha
        brain_sharp = Image.fromarray(bsharp_arr)
        icon_img.alpha_composite(brain_sharp)

        # Draw typography
        try:
            font_main = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 52)
        except Exception:
            font_main = ImageFont.load_default()

        t_draw = ImageDraw.Draw(icon_img)
        bbox = t_draw.textbbox((0, 0), app_title, font=font_main)
        tw = bbox[2] - bbox[0]
        tx = (1024 - tw) / 2
        ty = 724

        # Text drop glow
        t_glow = Image.new('RGBA', (1024, 1024), (0, 0, 0, 0))
        tg_draw = ImageDraw.Draw(t_glow)
        glow_color = (255, 26, 75, 140) if is_browser else (0, 225, 255, 150)
        tg_draw.text((tx, ty), app_title, font=font_main, fill=glow_color)
        t_glow = t_glow.filter(ImageFilter.GaussianBlur(8))
        icon_img.alpha_composite(t_glow)

        # Text crisp fill
        t_draw.text((tx, ty), app_title, font=font_main, fill=(245, 248, 255, 255))

        return icon_img

    print("Building radiant HugOS IDE icon...")
    ide_icon = build_icon("HUGOS IDE", is_browser=False)

    print("Building radiant HugOS Browser icon...")
    browser_icon = build_icon("HUGOS BROWSER", is_browser=True)

    # Save multi-size ICO helper
    def save_ico(img, out_path, sizes=[256, 128, 64, 48, 32, 16]):
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        icons = [img.resize((s, s), Image.LANCZOS) for s in sizes]
        icons[0].save(out_path, format='ICO', sizes=[(s, s) for s in sizes], append_images=icons[1:])
        print(f"Saved {out_path} ({os.path.getsize(out_path)} bytes)")

    # 1. Save IDE master files
    ide_icon.save(r'd:\harfile\ModelFusion\IDE\hugos_1024x1024.png', 'PNG')
    for sz in [512, 256, 128, 64, 48, 32, 16]:
        resized = ide_icon.resize((sz, sz), Image.LANCZOS)
        resized.save(rf'd:\harfile\ModelFusion\IDE\hugos_{sz}x{sz}.png', 'PNG')
    
    save_ico(ide_icon, r'd:\harfile\ModelFusion\IDE\hugos.ico')
    print("Updated IDE hugos.ico and PNGs")

    # 2. Save Browser master files
    save_ico(browser_icon, r'd:\harfile\ModelFusion\IDE\hugos_browser.ico')
    save_ico(browser_icon, r'd:\harfile\ModelFusion\browser\ui\hugos_browser.ico')
    save_ico(browser_icon, r'd:\harfile\ModelFusion\browser\ui\favicon.ico', sizes=[64, 48, 32, 16])

    # PNG icons for browser PWA / web
    browser_icon.resize((512, 512), Image.LANCZOS).save(r'd:\harfile\ModelFusion\browser\ui\icon-512.png', 'PNG')
    browser_icon.resize((192, 192), Image.LANCZOS).save(r'd:\harfile\ModelFusion\browser\ui\icon-192.png', 'PNG')
    browser_icon.resize((32, 32), Image.LANCZOS).save(r'd:\harfile\ModelFusion\browser\ui\favicon-32x32.png', 'PNG')
    browser_icon.resize((16, 16), Image.LANCZOS).save(r'd:\harfile\ModelFusion\browser\ui\favicon-16x16.png', 'PNG')
    print("Updated browser/ui PNGs and ICOs")

    # Check Chromium launcher directory
    chrom_ico = r'd:\harfile\ModelFusion\browser\Chromium-win32-x64\hugos_browser.ico'
    if os.path.exists(os.path.dirname(chrom_ico)):
        shutil.copy2(r'd:\harfile\ModelFusion\browser\ui\hugos_browser.ico', chrom_ico)
        print(f"Copied to {chrom_ico}")

    # Generate radiant SVG favicon for browser/ui/favicon.svg
    svg_content = generate_radiant_svg()
    with open(r'd:\harfile\ModelFusion\browser\ui\favicon.svg', 'w', encoding='utf-8') as f:
        f.write(svg_content)
    print("Updated browser/ui/favicon.svg")

def generate_radiant_svg():
    return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100%" height="100%">
  <defs>
    <!-- Deep Obsidian Dark Background Gradient -->
    <linearGradient id="obsidianGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#18122B"/>
      <stop offset="45%" stop-color="#0F1026"/>
      <stop offset="100%" stop-color="#070814"/>
    </linearGradient>

    <!-- Gemini-Inspired Radiant Gradient (Scarlet Red -> Coral -> Magenta -> Violet -> Cyan) -->
    <linearGradient id="geminiBorderGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FF1A4B"/>
      <stop offset="22%" stop-color="#FF6B35"/>
      <stop offset="44%" stop-color="#EE1E99"/>
      <stop offset="68%" stop-color="#8B2FE8"/>
      <stop offset="88%" stop-color="#00E5FF"/>
      <stop offset="100%" stop-color="#00FFB2"/>
    </linearGradient>

    <linearGradient id="neuralBrainGrad" x1="15%" y1="15%" x2="85%" y2="85%">
      <stop offset="0%" stop-color="#FF2A55"/>
      <stop offset="25%" stop-color="#FF7A30"/>
      <stop offset="50%" stop-color="#E81E99"/>
      <stop offset="75%" stop-color="#9333EA"/>
      <stop offset="100%" stop-color="#06B6D4"/>
    </linearGradient>

    <!-- Outer Ambient Glow Filter -->
    <filter id="outerGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="12" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>

    <filter id="synapseGlow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="6" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>

  <!-- Ambient Glow -->
  <rect x="24" y="24" width="464" height="464" rx="105" fill="#E81E99" opacity="0.18" filter="url(#outerGlow)"/>

  <!-- Squircle Obsidian Card -->
  <rect x="24" y="24" width="464" height="464" rx="105" fill="url(#obsidianGrad)"/>

  <!-- Radiant Gemini Border Stroke -->
  <rect x="24" y="24" width="464" height="464" rx="105" fill="none" stroke="url(#geminiBorderGrad)" stroke-width="6"/>

  <!-- Glowing Neural Brain Circuit Path -->
  <g id="neuralBrain" filter="url(#synapseGlow)" transform="translate(4, -10)">
    <!-- Left Hemisphere Lobes -->
    <path d="M 240,140 C 200,135 155,160 145,200 C 135,240 150,270 140,300 C 130,330 145,365 175,385 C 205,405 235,395 242,390"
          fill="none" stroke="url(#neuralBrainGrad)" stroke-width="7" stroke-linecap="round"/>
    
    <!-- Right Hemisphere Lobes -->
    <path d="M 264,140 C 304,135 349,160 359,200 C 369,240 354,270 364,300 C 374,330 359,365 329,385 C 299,405 269,395 262,390"
          fill="none" stroke="url(#neuralBrainGrad)" stroke-width="7" stroke-linecap="round"/>

    <!-- Central Sulcus / Fissure -->
    <line x1="252" y1="135" x2="252" y2="395" stroke="#E81E99" stroke-width="3.5" stroke-dasharray="8,6" opacity="0.8"/>

    <!-- Internal Neural Circuit Convolutions -->
    <path d="M 180,185 Q 210,195 235,175" fill="none" stroke="url(#neuralBrainGrad)" stroke-width="5" stroke-linecap="round"/>
    <path d="M 324,185 Q 294,195 269,175" fill="none" stroke="url(#neuralBrainGrad)" stroke-width="5" stroke-linecap="round"/>

    <path d="M 160,240 Q 200,230 235,250" fill="none" stroke="url(#neuralBrainGrad)" stroke-width="5" stroke-linecap="round"/>
    <path d="M 344,240 Q 304,230 269,250" fill="none" stroke="url(#neuralBrainGrad)" stroke-width="5" stroke-linecap="round"/>

    <path d="M 155,300 Q 195,310 235,295" fill="none" stroke="url(#neuralBrainGrad)" stroke-width="5" stroke-linecap="round"/>
    <path d="M 349,300 Q 309,310 269,295" fill="none" stroke="url(#neuralBrainGrad)" stroke-width="5" stroke-linecap="round"/>

    <path d="M 185,355 Q 215,340 240,360" fill="none" stroke="url(#neuralBrainGrad)" stroke-width="5" stroke-linecap="round"/>
    <path d="M 319,355 Q 289,340 264,360" fill="none" stroke="url(#neuralBrainGrad)" stroke-width="5" stroke-linecap="round"/>

    <!-- Brilliant Synapse Nodes (Pulsing Sparks) -->
    <circle cx="145" cy="200" r="6" fill="#FF1A4B"/>
    <circle cx="359" cy="200" r="6" fill="#FF6B35"/>
    <circle cx="140" cy="300" r="6" fill="#EE1E99"/>
    <circle cx="364" cy="300" r="6" fill="#9333EA"/>
    <circle cx="175" cy="385" r="5.5" fill="#8B2FE8"/>
    <circle cx="329" cy="385" r="5.5" fill="#00E5FF"/>
    
    <circle cx="235" cy="175" r="5" fill="#FFFFFF"/>
    <circle cx="269" cy="175" r="5" fill="#FFFFFF"/>
    <circle cx="235" cy="250" r="5.5" fill="#00FFB2"/>
    <circle cx="269" cy="250" r="5.5" fill="#00FFB2"/>
    <circle cx="235" cy="295" r="5" fill="#FFFFFF"/>
    <circle cx="269" cy="295" r="5" fill="#FFFFFF"/>
  </g>

  <!-- Title Monogram / Indicator -->
  <text x="256" y="445" font-family="'Segoe UI', -apple-system, sans-serif" font-size="25" font-weight="800"
        letter-spacing="4" fill="#FFFFFF" text-anchor="middle" opacity="0.95">HUGOS</text>
</svg>'''

if __name__ == '__main__':
    generate_radiant_suite()
