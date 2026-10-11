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

log_path = r"d:\harfile\ModelFusion\reports\tab3_click.log"
with open(log_path, "w", encoding="utf-8") as f:
    f.write("Switching to Tab 3 (Ctrl + 3)...\n")

# Switch to Tab 3
VK_CONTROL = 0x11
VK_3 = 0x33

user32.keybd_event(VK_CONTROL, 0, 0, 0)
time.sleep(0.05)
user32.keybd_event(VK_3, 0, 0, 0)
time.sleep(0.05)
user32.keybd_event(VK_3, 0, 0x0002, 0)
time.sleep(0.05)
user32.keybd_event(VK_CONTROL, 0, 0x0002, 0)
time.sleep(1.5)

with open(log_path, "a", encoding="utf-8") as f:
    f.write("Sending normalized SendInput click to (666, 537)...\n")

click_screen(666, 537)
time.sleep(3.0)

shot_path = r"d:\harfile\ModelFusion\reports\tab3_after_click.png"
img = ImageGrab.grab()
img.save(shot_path)

with open(log_path, "a", encoding="utf-8") as f:
    f.write(f"Saved screenshot: {shot_path}\n")
