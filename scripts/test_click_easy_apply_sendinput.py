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
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

def click_pos(x, y):
    user32.SetCursorPos(x, y)
    time.sleep(0.15)
    
    inp_down = INPUT(type=INPUT_MOUSE)
    inp_down.mi.dwFlags = MOUSEEVENTF_LEFTDOWN
    user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))
    time.sleep(0.1)
    
    inp_up = INPUT(type=INPUT_MOUSE)
    inp_up.mi.dwFlags = MOUSEEVENTF_LEFTUP
    user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))
    time.sleep(0.2)

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

log_file = r"d:\harfile\ModelFusion\reports\sendinput_click.log"
with open(log_file, "w", encoding="utf-8") as f:
    f.write(f"Focusing Chrome: {target}\n")

bring_to_front(target[0])
time.sleep(1.0)

# Activate by clicking inside page content
click_pos(1000, 300)
time.sleep(0.5)

# Click Easy Apply button at (666, 537)
with open(log_file, "a", encoding="utf-8") as f:
    f.write("Sending SendInput click to (666, 537)...\n")

click_pos(666, 537)
time.sleep(3.0)

# Capture screen
shot_path = r"d:\harfile\ModelFusion\reports\modal_step2.png"
img = ImageGrab.grab()
img.save(shot_path)

with open(log_file, "a", encoding="utf-8") as f:
    f.write(f"Captured screen to {shot_path}\n")
