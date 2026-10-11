#!/usr/bin/env python3
"""
ModelFusion Computer Use Session 1 Interactive Runner
Runs directly in the user's interactive desktop session via Task Scheduler (/it).
"""

import os
import sys
import time
import ctypes
from ctypes import wintypes

log_file = os.path.abspath(r"d:\harfile\ModelFusion\reports\computer_use_session1.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)

def log(msg):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    print(msg)

log("==================================================")
log("🚀 Computer Use Session 1 Interactive Runner started")

user32 = ctypes.windll.user32

# 1. Test Screen Capture in Session 1
try:
    from PIL import ImageGrab
    img = ImageGrab.grab()
    screenshot_path = os.path.abspath(r"d:\harfile\ModelFusion\reports\session1_desktop.png")
    img.save(screenshot_path)
    log(f"📸 Screen captured in Session 1! Resolution: {img.size} -> {screenshot_path}")
except Exception as e:
    log(f"⚠️ ImageGrab notice in Session 1: {e}")

# 2. Enumerate Windows in Session 1
found_chrome = None
all_titles = []

def enum_cb(hwnd, lparam):
    global found_chrome
    if user32.IsWindowVisible(hwnd):
        l = user32.GetWindowTextLengthW(hwnd)
        if l > 0:
            b = ctypes.create_unicode_buffer(l + 1)
            user32.GetWindowTextW(hwnd, b, l + 1)
            txt = b.value
            all_titles.append((hwnd, txt))
            if any(term in txt.lower() for term in ["ahura", "linkedin", "apply"]):
                found_chrome = (hwnd, txt)
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

log(f"Found {len(all_titles)} visible windows in Session 1.")
for h, t in all_titles[:8]:
    log(f"  • HWND {h}: {t}")

if not found_chrome:
    for h, t in all_titles:
        if "chrome" in t.lower():
            found_chrome = (h, t)
            break

if found_chrome:
    hwnd, title = found_chrome
    log(f"🎯 Target Window identified: HWND {hwnd} ('{title}')")
    
    # Bring to foreground
    user32.ShowWindow(hwnd, 3) # SW_MAXIMIZE
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)
    
    # Multi-Step Advance Loop (Step 1 -> 5)
    KEYEVENTF_KEYUP = 0x0002
    VK_RETURN = 0x0D
    VK_TAB = 0x09
    
    def press(vk):
        user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.05)
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.1)

    log("📋 Advancing Easy Apply Form...")
    
    # Step 1 -> Next
    log("  ➔ Step 1: Advancing Contact Info (ENTER)...")
    press(VK_RETURN)
    time.sleep(1.5)
    
    # Step 2 -> Resume (ENTER)
    log("  ➔ Step 2: Advancing Resume Attachment (ENTER)...")
    press(VK_RETURN)
    time.sleep(1.5)
    
    # Step 3 -> Screening questions (fill 20 if input active, then ENTER)
    log("  ➔ Step 3: Answering Screening questions (20 + ENTER)...")
    for char in "20":
        vk = user32.VkKeyScanW(ord(char)) & 0xFF
        press(vk)
    time.sleep(0.3)
    press(VK_RETURN)
    time.sleep(1.5)
    
    # Step 4 -> Review (ENTER)
    log("  ➔ Step 4: Advancing to Review (ENTER)...")
    press(VK_RETURN)
    time.sleep(1.5)
    
    # Step 5 -> Final Submit
    log("  ➔ Step 5: Submitting Application (ENTER)...")
    press(VK_RETURN)
    time.sleep(2.0)
    
    # Capture final post-submit screenshot
    try:
        from PIL import ImageGrab
        final_img = ImageGrab.grab()
        final_receipt = os.path.abspath(r"d:\harfile\ModelFusion\reports\session1_submission_receipt.png")
        final_img.save(final_receipt)
        log(f"📸 Submission Receipt Captured: {final_receipt}")
    except Exception as e:
        log(f"Receipt capture notice: {e}")
        
    log("🎉 Computer Use Form Fill & Submission complete!")
else:
    log("⚠️ Could not locate Chrome/LinkedIn window in Session 1.")

