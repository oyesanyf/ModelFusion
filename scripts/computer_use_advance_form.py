#!/usr/bin/env python3
"""
ModelFusion Computer Use OS Agent
Advances the active LinkedIn Easy Apply form on the user's desktop.
"""

import time
import sys
import ctypes

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

user32 = ctypes.windll.user32

def find_and_activate_chrome():
    found_hwnd = None
    
    def enum_windows_callback(hwnd, extra):
        nonlocal found_hwnd
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value
            if any(term in title.lower() for term in ["linkedin", "apply", "ahura", "chrome"]):
                found_hwnd = hwnd
                return False
        return True

    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))
    user32.EnumWindows(EnumWindowsProc(enum_windows_callback), 0)

    if found_hwnd:
        user32.ShowWindow(found_hwnd, 3) # SW_MAXIMIZE
        user32.SetForegroundWindow(found_hwnd)
        time.sleep(0.3)
        return True
    return False

def press_key(vk_code):
    KEYEVENTF_KEYUP = 0x0002
    user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.1)

def type_text(text):
    for char in text:
        vk = user32.VkKeyScanW(ord(char))
        if vk != -1:
            shift = (vk >> 8) & 1
            code = vk & 0xFF
            if shift:
                user32.keybd_event(0x10, 0, 0, 0) # SHIFT down
            press_key(code)
            if shift:
                user32.keybd_event(0x10, 0, 0x0002, 0) # SHIFT up
            time.sleep(0.03)

def click_next_or_submit():
    print("[COMPUTER USE] 🖥️ Activating LinkedIn window...")
    if not find_and_activate_chrome():
        print("⚠️ Could not find active LinkedIn/Chrome window.")
        return False

    print("[COMPUTER USE] 🎯 Grounding Next/Submit button on active form...")
    # Enter key triggers the primary button in the dialog
    VK_RETURN = 0x0D
    press_key(VK_RETURN)
    print("  ✓ Sent trigger (ENTER) to advance form.")
    return True

if __name__ == "__main__":
    click_next_or_submit()
