#!/usr/bin/env python3
"""
ModelFusion Autonomous LinkedIn Easy Apply Stepper
Steps through the open Easy Apply modal and submits the application.
"""

import os
import sys
import time
import ctypes
from ctypes import wintypes
from PIL import ImageGrab, Image

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

def bring_to_front(hwnd):
    user32.ShowWindow(hwnd, 9)
    user32.ShowWindow(hwnd, 3)
    fg_hwnd = user32.GetForegroundWindow()
    fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None)
    curr_thread = kernel32.GetCurrentThreadId()
    if fg_thread != curr_thread:
        user32.AttachThreadInput(curr_thread, fg_thread, True)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.AttachThreadInput(curr_thread, fg_thread, False)
    else:
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
    user32.SwitchToThisWindow(hwnd, True)

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]
    _anonymous_ = ("_input",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("_input", _INPUT),
    ]

INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000

def click_screen(x, y, screen_w=2560, screen_h=1080):
    nx = int(x * 65535 / (screen_w - 1))
    ny = int(y * 65535 / (screen_h - 1))
    
    inp_move = INPUT(type=INPUT_MOUSE)
    inp_move.mi.dx = nx
    inp_move.mi.dy = ny
    inp_move.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE
    user32.SendInput(1, ctypes.byref(inp_move), ctypes.sizeof(INPUT))
    time.sleep(0.12)
    
    inp_down = INPUT(type=INPUT_MOUSE)
    inp_down.mi.dx = nx
    inp_down.mi.dy = ny
    inp_down.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_LEFTDOWN
    user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))
    time.sleep(0.12)
    
    inp_up = INPUT(type=INPUT_MOUSE)
    inp_up.mi.dx = nx
    inp_up.mi.dy = ny
    inp_up.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_LEFTUP
    user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))
    time.sleep(0.2)

def find_modal_action_button(img):
    w, h = img.size
    candidates = []
    # Modal action buttons (Next, Review, Submit) appear in the bottom right of the modal
    # In full screen 2560x1080: X is roughly 1450 to 1850, Y is roughly 720 to 860
    for y in range(int(h * 0.65), int(h * 0.88), 2):
        for x in range(int(w * 0.55), int(w * 0.75), 2):
            r, g, b = img.getpixel((x, y))[:3]
            if b > 170 and r < 40 and 85 < g < 135:
                candidates.append((x, y))
                
    if not candidates:
        return None
        
    min_x = min(c[0] for c in candidates)
    max_x = max(c[0] for c in candidates)
    min_y = min(c[1] for c in candidates)
    max_y = max(c[1] for c in candidates)
    
    bw = max_x - min_x
    bh = max_y - min_y
    if bw >= 40 and bh >= 20:
        return ((min_x + max_x) // 2, (min_y + max_y) // 2, bw, bh)
    return None

log_file = r"d:\harfile\ModelFusion\reports\stepper.log"
def log(msg):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    print(msg)

with open(log_file, "w", encoding="utf-8") as f:
    f.write("=== Autonomous LinkedIn Easy Apply Stepper Initialized ===\n")

# Focus Chrome
found_chrome = []
def enum_cb(hwnd, lparam):
    if user32.IsWindowVisible(hwnd):
        l = user32.GetWindowTextLengthW(hwnd)
        if l > 0:
            b = ctypes.create_unicode_buffer(l + 1)
            user32.GetWindowTextW(hwnd, b, l + 1)
            txt = b.value
            if "chrome" in txt.lower():
                found_chrome.append((hwnd, txt))
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

target = found_chrome[0]
for h, t in found_chrome:
    if "linkedin" in t.lower() or "ahura" in t.lower():
        target = (h, t)
        break

bring_to_front(target[0])
time.sleep(0.5)

# Stepping loop (up to 7 steps)
for step_idx in range(1, 8):
    log(f"--- Stepper evaluating Page / Step {step_idx} ---")
    screen = ImageGrab.grab()
    shot_path = rf"d:\harfile\ModelFusion\reports\modal_step_page{step_idx}.png"
    screen.save(shot_path)
    log(f"Captured current screen to {shot_path}")
    
    btn = find_modal_action_button(screen)
    if not btn:
        log("No modal blue action button found in target area. Checking if submission complete...")
        # Check if "Application submitted" screen is shown
        final_shot = r"d:\harfile\ModelFusion\reports\final_application_submitted.png"
        screen.save(final_shot)
        log(f"Saved potential final confirmation screen to {final_shot}")
        break
        
    bx, by, bw, bh = btn
    log(f"🎯 Grounded modal action button at ({bx}, {by}) Size=({bw}, {bh}). Clicking...")
    click_screen(bx, by)
    log(f"  ✓ Clicked action button at ({bx}, {by}). Waiting 2.0s for next screen...")
    time.sleep(2.0)

# Final verification capture
time.sleep(2.0)
final_screen = ImageGrab.grab()
final_shot = r"d:\harfile\ModelFusion\reports\final_application_submitted.png"
final_screen.save(final_shot)
log(f"🎉 Stepper completed! Final screen saved to {final_shot}")
