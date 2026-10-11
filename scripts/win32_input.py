import ctypes
from ctypes import wintypes
import time

user32 = ctypes.windll.user32

# Define INPUT structure for SendInput
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

def click_pos(x, y):
    # Set cursor
    user32.SetCursorPos(x, y)
    time.sleep(0.1)
    
    # SendInput down
    inp_down = INPUT(type=INPUT_MOUSE)
    inp_down.mi.dx = 0
    inp_down.mi.dy = 0
    inp_down.mi.mouseData = 0
    inp_down.mi.dwFlags = MOUSEEVENTF_LEFTDOWN
    inp_down.mi.time = 0
    inp_down.mi.dwExtraInfo = None
    user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))
    
    time.sleep(0.12)
    
    # SendInput up
    inp_up = INPUT(type=INPUT_MOUSE)
    inp_up.mi.dx = 0
    inp_up.mi.dy = 0
    inp_up.mi.mouseData = 0
    inp_up.mi.dwFlags = MOUSEEVENTF_LEFTUP
    inp_up.mi.time = 0
    inp_up.mi.dwExtraInfo = None
    user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))

print("INPUT definition valid.")
