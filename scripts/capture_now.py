#!/usr/bin/env python3
import os
import sys
from PIL import ImageGrab

out = os.path.abspath(r"d:\harfile\ModelFusion\reports\current_desktop.png")
try:
    img = ImageGrab.grab()
    img.save(out)
    print(f"Captured {img.size} to {out}")
except Exception as e:
    print(f"Error: {e}")
