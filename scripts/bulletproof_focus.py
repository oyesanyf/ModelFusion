#!/usr/bin/env python3
import time
import ctypes
from ctypes import wintypes
from PIL import ImageGrab

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

def force_chrome_foreground():
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

    target_hwnd = None
    for h, t in found:
        if "linkedin" in t.lower() or "ahura" in t.lower():
            target_hwnd = h
            break
    if not target_hwnd and found:
        target_hwnd = found[0][0]

    if not target_hwnd:
        return False

    for attempt in range(5):
        # Un-minimize
        user32.ShowWindow(target_hwnd, 9) # SW_RESTORE
        user32.ShowWindow(target_hwnd, 3) # SW_MAXIMIZE
        
        # ALT-key bypass
        user32.keybd_event(0x12, 0, 0, 0)
        time.sleep(0.02)
        user32.keybd_event(0x12, 0, 2, 0)
        time.sleep(0.02)
        
        user32.BringWindowToTop(target_hwnd)
        user32.SetForegroundWindow(target_hwnd)
        user32.SwitchToThisWindow(target_hwnd, True)
        time.sleep(0.4)
        
        if user32.GetForegroundWindow() == target_hwnd:
            return True
            
    return False

if __name__ == "__main__":
    ok = force_chrome_foreground()
    time.sleep(0.8)
    shot = ImageGrab.grab()
    shot.save(r"d:\harfile\ModelFusion\reports\bulletproof_screen.png")
    print(f"Brought to front: {ok}, saved to bulletproof_screen.png")
