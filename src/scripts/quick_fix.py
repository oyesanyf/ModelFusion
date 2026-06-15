#!/usr/bin/env python3
"""
Quick fix for missing aiohttp module.
"""

import subprocess
import sys

def main():
    print("🔧 Quick Fix: Installing missing aiohttp module")
    print("=" * 40)
    
    try:
        print("Installing aiohttp...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "aiohttp"])
        print("✅ Successfully installed aiohttp!")
        
        print("\n🎉 Quick fix complete!")
        print("You can now run: python HuggingFace_orhcestrator.py --help")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install aiohttp: {e}")
        print("\n💡 Alternative solutions:")
        print("  1. Try: pip install aiohttp")
        print("  2. Run: python install_dependencies.py")
        print("  3. Check your Python environment")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 