#!/usr/bin/env python3
import os
import sys
import time
import ctypes
from ctypes import wintypes
from PIL import ImageGrab, Image

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

def bring_to_front(hwnd):
    user32.ShowWindow(hwnd, 9) # SW_RESTORE
    user32.ShowWindow(hwnd, 3) # SW_MAXIMIZE
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

def hardware_click(x, y):
    user32.SetCursorPos(x, y)
    time.sleep(0.08)
    user32.mouse_event(0x0002, 0, 0, 0, 0) # LEFTDOWN
    time.sleep(0.06)
    user32.mouse_event(0x0004, 0, 0, 0, 0) # LEFTUP
    time.sleep(0.3)

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

target = None
for h, t in found_chrome:
    if "linkedin" in t.lower() or "ahura" in t.lower():
        target = (h, t)
        break

if not target and found_chrome:
    target = found_chrome[0]

log_file = r"d:\harfile\ModelFusion\reports\step1_click.log"
with open(log_file, "w", encoding="utf-8") as f:
    f.write(f"Focusing {target}\n")

bring_to_front(target[0])
time.sleep(1.0)

# Click Easy Apply at (666, 537)
with open(log_file, "a", encoding="utf-8") as f:
    f.write("Clicking Easy Apply button at (666, 537)...\n")

hardware_click(666, 537)
time.sleep(2.5) # Wait for modal

# Capture screen after click
shot_path = r"d:\harfile\ModelFusion\reports\modal_step1.png"
img = ImageGrab.grab()
img.save(shot_path)

with open(log_file, "a", encoding="utf-8") as f:
    f.write(f"Captured modal state to {shot_path} ({img.size})\n")
