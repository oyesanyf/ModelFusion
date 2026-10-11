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

# Send Ctrl + 1
VK_CONTROL = 0x11
VK_1 = 0x31

user32.keybd_event(VK_CONTROL, 0, 0, 0)
time.sleep(0.05)
user32.keybd_event(VK_1, 0, 0, 0)
time.sleep(0.05)
user32.keybd_event(VK_1, 0, 0x0002, 0)
time.sleep(0.05)
user32.keybd_event(VK_CONTROL, 0, 0x0002, 0)
time.sleep(1.0)

# Capture screen
shot_path = r"d:\harfile\ModelFusion\reports\tab1_screen.png"
img = ImageGrab.grab()
img.save(shot_path)
print(f"Switched to Tab 1 and saved to {shot_path}")
