#!/usr/bin/env python3
"""
ModelFusion Full Autonomous LinkedIn Job Application Engine
Brings up the LinkedIn job, clicks Easy Apply, steps through the modal, and submits.
"""

import os
import sys
import time
import ctypes
from ctypes import wintypes
from PIL import ImageGrab

log_file = os.path.abspath(r"d:\harfile\ModelFusion\reports\auto_apply_clicker.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)

def log(msg):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    print(msg)

log("==================================================")
log("🚀 Full Autonomous Computer Use Flow Initialized")

user32 = ctypes.windll.user32

# 1. Ensure target LinkedIn tab is active
target_url = "https://www.linkedin.com/jobs/view/principal-ai-security-lead-architect-100%25-remote-at-ahura-workforce-solutions-4476846948"
log(f"🌐 Launching/focusing target job URL: {target_url}")
os.system(f'start "" "{target_url}"')
time.sleep(5.0) # Wait for page load

# 2. Find and activate Chrome window
found_chrome = None
def enum_cb(hwnd, lparam):
    global found_chrome
    if user32.IsWindowVisible(hwnd):
        l = user32.GetWindowTextLengthW(hwnd)
        if l > 0:
            b = ctypes.create_unicode_buffer(l + 1)
            user32.GetWindowTextW(hwnd, b, l + 1)
            txt = b.value
            if "chrome" in txt.lower():
                if not found_chrome or "linkedin" in txt.lower() or "ahura" in txt.lower():
                    found_chrome = (hwnd, txt)
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

if found_chrome:
    hwnd, title = found_chrome
    log(f"🎯 Activating Chrome: HWND {hwnd} ('{title}')")
    user32.ShowWindow(hwnd, 3) # SW_MAXIMIZE
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.8)

def find_primary_blue_button(img):
    w, h = img.size
    candidates = []
    # Search from Y: 20% to 92%, X: 15% to 85%
    for y in range(int(h * 0.20), int(h * 0.92), 2):
        for x in range(int(w * 0.15), int(w * 0.85), 2):
            r, g, b = img.getpixel((x, y))[:3]
            # LinkedIn button blue #0a66c2
            if b > 165 and r < 45 and 75 < g < 145:
                candidates.append((x, y))
                
    if not candidates:
        return None
        
    # Pick lowest cluster (the bottom action button)
    max_y = max(c[1] for c in candidates)
    bottom_candidates = [c for c in candidates if c[1] >= max_y - 45]
    if not bottom_candidates:
        return None
        
    min_x = min(c[0] for c in bottom_candidates)
    max_x = max(c[0] for c in bottom_candidates)
    min_y = min(c[1] for c in bottom_candidates)
    max_y = max(c[1] for c in bottom_candidates)
    
    bw = max_x - min_x
    bh = max_y - min_y
    if 35 <= bw <= 350 and 15 <= bh <= 75:
        return ((min_x + max_x)//2, (min_y + max_y)//2, bw, bh)
    return None

def hardware_click(x, y):
    log(f"👆 Clicking at ({x}, {y})...")
    user32.SetCursorPos(x, y)
    time.sleep(0.08)
    user32.mouse_event(0x0002, 0, 0, 0, 0) # LEFTDOWN
    time.sleep(0.06)
    user32.mouse_event(0x0004, 0, 0, 0, 0) # LEFTUP
    time.sleep(0.3)

# 3. Step 0: Click initial "Easy Apply" button on the job posting
log("🔍 Step 0: Searching for 'Easy Apply' button on job posting...")
screen = ImageGrab.grab()
btn = find_primary_blue_button(screen)
if btn:
    bx, by, bw, bh = btn
    log(f"🎯 Found Easy Apply button at ({bx}, {by}). Clicking...")
    hardware_click(bx, by)
    time.sleep(2.5) # Wait for modal animation
else:
    log("ℹ️ No initial Easy Apply button found; modal may already be open.")

# 4. Multi-Step Modal Advancement Loop
for step in range(1, 7):
    time.sleep(1.2)
    screen = ImageGrab.grab()
    btn = find_primary_blue_button(screen)
    if not btn:
        log(f"ℹ️ Modal step {step}: No primary button visible. Application likely submitted or closed.")
        receipt = os.path.abspath(r"d:\harfile\ModelFusion\reports\auto_apply_submitted_screen.png")
        screen.save(receipt)
        log(f"📸 Saved final state to {receipt}")
        break
        
    bx, by, bw, bh = btn
    log(f"🎯 Modal Step {step}: Action button grounded at ({bx}, {by}).")
    
    # If on questions step, ensure '20' is filled
    if step in [3, 4]:
        for char in "20":
            vk = user32.VkKeyScanW(ord(char)) & 0xFF
            user32.keybd_event(vk, 0, 0, 0)
            time.sleep(0.03)
            user32.keybd_event(vk, 0, 0x0002, 0)
        time.sleep(0.2)
        
    hardware_click(bx, by)
    log(f"  ✓ Clicked Step {step} action button.")
    time.sleep(2.0)

log("🎉 Complete autonomous loop finished!")
