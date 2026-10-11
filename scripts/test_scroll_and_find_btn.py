#!/usr/bin/env python3
import os
import sys
import time
import ctypes
from ctypes import wintypes
from PIL import ImageGrab

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

def scroll_modal(x=1300, y=500, delta=-600):
    user32.SetCursorPos(x, y)
    time.sleep(0.1)
    # WHEEL DOWN
    user32.mouse_event(0x0800, 0, 0, ctypes.c_ulong(delta).value, 0)
    time.sleep(0.3)
    user32.mouse_event(0x0800, 0, 0, ctypes.c_ulong(delta).value, 0)
    time.sleep(0.5)

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
bring_to_front(target[0])
time.sleep(0.5)

log_path = r"d:\harfile\ModelFusion\reports\scroll_test.log"
with open(log_path, "w", encoding="utf-8") as f:
    f.write("Scrolling modal at (1300, 500)...\n")

scroll_modal(1300, 500, -800)

shot_path = r"d:\harfile\ModelFusion\reports\modal_after_scroll.png"
img = ImageGrab.grab()
img.save(shot_path)

with open(log_path, "a", encoding="utf-8") as f:
    f.write(f"Saved screen to {shot_path}\n")
