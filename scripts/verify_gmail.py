#!/usr/bin/env python3
import time
import ctypes
from ctypes import wintypes
from PIL import ImageGrab

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

def bring_to_front(hwnd):
    user32.ShowWindow(hwnd, 9)
    user32.ShowWindow(hwnd, 3)
    user32.keybd_event(0x12, 0, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(0x12, 0, 2, 0)
    time.sleep(0.02)
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    user32.SwitchToThisWindow(hwnd, True)

found = []
def enum_cb(hwnd, lparam):
    if user32.IsWindowVisible(hwnd):
        l = user32.GetWindowTextLengthW(hwnd)
        if l > 0:
            b = ctypes.create_unicode_buffer(l + 1)
            user32.GetWindowTextW(hwnd, b, l + 1)
            txt = b.value
            if "chrome" in txt.lower():
                found.append((hwnd, txt))
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

target = found[0][0]
bring_to_front(target)
time.sleep(0.5)

# Switch to Tab 2 (Gmail)
VK_CONTROL = 0x11
VK_2 = 0x32
user32.keybd_event(VK_CONTROL, 0, 0, 0)
time.sleep(0.05)
user32.keybd_event(VK_2, 0, 0, 0)
time.sleep(0.05)
user32.keybd_event(VK_2, 0, 0x0002, 0)
time.sleep(0.05)
user32.keybd_event(VK_CONTROL, 0, 0x0002, 0)
time.sleep(1.0)

# Refresh page (F5)
VK_F5 = 0x74
user32.keybd_event(VK_F5, 0, 0, 0)
time.sleep(0.05)
user32.keybd_event(VK_F5, 0, 0x0002, 0)
time.sleep(4.0)

shot = ImageGrab.grab()
shot_path = r"d:\harfile\ModelFusion\reports\gmail_verification.png"
shot.save(shot_path)
print(f"Captured refreshed Gmail to {shot_path}")
